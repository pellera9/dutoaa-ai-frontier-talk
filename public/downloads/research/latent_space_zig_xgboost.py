#!/usr/bin/env python3
"""Paper-inspired, verified censored power-Gamma hurdle boosting.

Paper: Wang, arXiv:2608.26286v2 (2026), equations 1, 9--16, 22--33.
This is an independently written educational implementation, not author code.
It uses the valid censored likelihood rather than reproducing the problematic
boundary saturated constant or the asserted null profiling identity in 18/34/35.
Run: python latent_space_zig_xgboost.py --self-test --rows 5000 --rounds 250
Requires numpy, scipy and xgboost>=3.0; matplotlib is optional for SVG exports.
"""
from __future__ import annotations
import argparse
import csv
from dataclasses import dataclass, asdict
import json
import math
import os
from pathlib import Path
import platform
import sys
import tempfile
import warnings

import numpy as np
import scipy
from scipy.integrate import quad
from scipy.optimize import minimize, minimize_scalar
from scipy.special import expit, gammainc, gammaincc, gammaln, logsumexp, ndtr
import xgboost as xgb


@dataclass(frozen=True)
class Structure:
    s: float
    lam: float
    alpha: float
    cap: float

    def __post_init__(self):
        if not (0 < self.s < self.cap and 0 < self.lam <= 1 and self.alpha > 0):
            raise ValueError('Require 0<s<U, 0<lambda<=1, alpha>0; lambda=1 is the censored-Gamma control.')

    @property
    def upper(self):
        return (self.cap/self.s)**self.lam


def transform(y, structure):
    """Eq. 1. The caller retains censor indicators from raw y>=U, before clipping."""
    y=np.asarray(y,dtype=float)
    if np.any(~np.isfinite(y)) or np.any(y<0):
        raise ValueError('Loss observations must be finite and nonnegative.')
    return (np.minimum(y,structure.cap)/structure.s)**structure.lam


def gamma_terms(alpha, z):
    """Return log Q(alpha,z), R, and the boundary eta-Hessian.

    Q = gammaincc = Gamma(alpha,z)/Gamma(alpha); R = z*f_unit_gamma(z)/Q.
    Ordinary range: log-domain SciPy evaluation. Deep tail: upper-Gamma
    continued fraction, so Q underflow never turns the score into zero.
    Very large z: explicitly differentiated expansion avoids cancellation in
    R*(alpha-z+R). That branch is an implementation approximation, not Eq. 27
    evaluated by subtracting three enormous nearly cancelling floats.
    """
    z=np.asarray(z,dtype=float)
    if alpha<=0 or np.any(~np.isfinite(z)) or np.any(z<=0):
        raise ValueError('Gamma arguments must be finite and strictly positive.')
    original_shape=z.shape
    x=z.reshape(-1)
    logq=np.empty_like(x);r=np.empty_like(x);h=np.empty_like(x)
    extreme=x>max(1e5,1000*alpha*alpha)
    low=x<alpha+1
    if np.any(low):
        xx=x[low];q=gammaincc(alpha,xx)
        logq[low]=np.log(q)
        r[low]=np.exp(alpha*np.log(xx)-xx-gammaln(alpha)-logq[low])
        h[low]=r[low]*(alpha-xx+r[low])
    middle=~low & ~extreme
    if np.any(middle):
        xx=x[middle]
        # Lentz's continued fraction: Gamma(a,x)=exp(-x)*x**a*cf.
        # Numerical Recipes/DLMF-style evaluation; vectorized across rows.
        tiny=1e-300;b=xx+1-alpha
        c=np.full_like(xx,1/tiny);d=1/b;cf=d.copy()
        for i in range(1,10001):
            an=-i*(i-alpha);b=b+2
            d=an*d+b;d=np.where(np.abs(d)<tiny,tiny,d)
            c=b+an/c;c=np.where(np.abs(c)<tiny,tiny,c)
            d=1/d;delta=d*c;cf*=delta
            if np.all(np.abs(delta-1)<2e-14):break
        else:raise ArithmeticError('Upper-Gamma continued fraction did not converge.')
        rr=1/cf
        r[middle]=rr
        logq[middle]=-xx+alpha*np.log(xx)-gammaln(alpha)-np.log(rr)
        h[middle]=rr*(alpha-xx+rr)
    if np.any(extreme):
        xx=x[extreme];b=alpha-1;c=b*(alpha-3)
        rr=xx-b+b/xx+c/(xx*xx)
        r[extreme]=rr
        logq[extreme]=-xx+alpha*np.log(xx)-gammaln(alpha)-np.log(rr)
        h[extreme]=xx-b/xx-2*c/(xx*xx)
    if np.any(h< -1e-10) or np.any(~np.isfinite(logq+r+h)):
        raise ArithmeticError('Invalid Gamma survival curvature.')
    return tuple(a.reshape(original_shape) for a in (logq,r,np.maximum(h,0)))


def log_lower_regularized(a,z):
    """Stable log P(a,z); a power series handles underflow of gammainc."""
    z=np.asarray(z,dtype=float)
    with np.errstate(divide='ignore'):
        result=np.log(gammainc(a,z))
    bad=~np.isfinite(result)
    if np.any(bad):
        xx=z[bad];term=np.full_like(xx,1/a);total=term.copy()
        for j in range(1,10001):
            term*=xx/(a+j);total+=term
            if np.all(np.abs(term)<2e-15*np.abs(total)):break
        else:raise ArithmeticError('Lower-Gamma series did not converge.')
        result[bad]=-xx+a*np.log(xx)-gammaln(a)+np.log(total)
    return result


def bounded_positive_mean(eta,structure):
    """Eq.16 without pi: E[min(s*T**(1/lambda),U)], T~Gamma(alpha,rate).

    This integral is NOT s*exp(eta/lambda). Work in log coordinates for the
    lower moment and use Q directly for the capped tail; avoid 1-gammainc.
    """
    eta=np.atleast_1d(np.asarray(eta,dtype=float))
    alpha=structure.alpha;q=1/structure.lam
    logbeta=np.log(alpha)-eta
    z=np.exp(logbeta+np.log(structure.upper))
    logq,_,_=gamma_terms(alpha,z)
    logmoment=(np.log(structure.s)-q*logbeta+gammaln(alpha+q)-gammaln(alpha)
               +log_lower_regularized(alpha+q,z))
    # Each term is mathematically bounded by U; caps here only guard rounding.
    body=np.exp(np.minimum(logmoment,np.log(structure.cap)))
    tail=structure.cap*np.exp(logq)
    return np.clip(body+tail,0,structure.cap)


def severity_nll(y_star,censored,eta,structure,raw_y=None):
    """Conditional negative log-likelihood, Eq.14; all supplied rows are positive.

    When structural parameters vary, include the transformation Jacobian on
    ordinary rows. There is no Jacobian for the discrete censored probability.
    Omitting it would compare densities in changing response coordinates.
    """
    y_star=np.asarray(y_star,float);eta=np.asarray(eta,float)
    censored=np.asarray(censored,bool);ordinary=~censored
    a=structure.alpha;logbeta=np.log(a)-eta;loss=np.empty_like(y_star)
    loss[ordinary]=(-a*logbeta[ordinary]+gammaln(a)
                    -(a-1)*np.log(y_star[ordinary])
                    +np.exp(logbeta[ordinary])*y_star[ordinary])
    if np.any(censored):
        z=np.exp(logbeta[censored]+np.log(structure.upper))
        loss[censored]=-gamma_terms(a,z)[0]
    if raw_y is not None:
        raw_y=np.asarray(raw_y,float)
        logjac=(np.log(structure.lam)-np.log(structure.s)
                +(structure.lam-1)*np.log(raw_y[ordinary]/structure.s))
        loss[ordinary]-=logjac
    return loss


def severity_derivatives(y_star,censored,eta,structure):
    """Exact ordinary Eq.25/27 and stable censored Eq.24/27 derivatives."""
    y_star=np.asarray(y_star,float);eta=np.asarray(eta,float)
    censored=np.asarray(censored,bool)
    if np.any(np.abs(eta)>60):
        raise FloatingPointError('Severity margin outside safe exponential range; reduce learning rate or max_delta_step.')
    ratio=y_star*np.exp(-eta)
    g=structure.alpha*(1-ratio);h=structure.alpha*ratio
    if np.any(censored):
        z=structure.alpha*structure.upper*np.exp(-eta[censored])
        _,r,curvature=gamma_terms(structure.alpha,z)
        g[censored]=-r;h[censored]=curvature
    return g,h


def fit_null_structure(y,cap,s,lambdas):
    """Training-only raw-scale censored likelihood calibration.

    IMPLEMENTATION CHOICE: fix s as an identifiable coordinate convention;
    grid lambda, optimize log-alpha and eta numerically, retain a fixed frame
    for boosting. This replaces the false Eq.34 censored-mean identity and
    does not minimize parameter-dependent saturated constants from Eq.21.
    """
    positive=np.asarray(y)[np.asarray(y)>0];censored=positive>=cap
    candidates=[]
    for lam in lambdas:
        base=Structure(s,lam,2,cap);t=transform(positive,base)
        eta0=np.log(np.mean(t))
        def objective(v):
            structure=Structure(s,lam,float(np.exp(v[0])),cap)
            eta=np.full(len(t),v[1])
            return float(np.mean(severity_nll(t,censored,eta,structure,positive)))
        result=minimize(objective,[np.log(2),eta0],method='L-BFGS-B',
                        bounds=[(np.log(.25),np.log(40)),(-15,15)],options={'maxiter':250})
        if not result.success or not np.isfinite(result.fun):
            raise RuntimeError('Structural fit failed: '+str(result.message))
        candidates.append({'lambda':float(lam),'alpha':float(np.exp(result.x[0])),
                           'eta0':float(result.x[1]),'training_raw_nll':float(result.fun)})
    best=min(candidates,key=lambda c:c['training_raw_nll'])
    return Structure(s,best['lambda'],best['alpha'],cap),best['eta0'],candidates


def joint_derivatives(pred,y_star,occur,censored,structure):
    pred=np.asarray(pred,float).reshape(-1,2)
    pi=expit(pred[:,0]);g=np.zeros_like(pred);h=np.zeros_like(pred)
    g[:,0]=pi-occur;h[:,0]=pi*(1-pi)
    positive=occur.astype(bool)
    g[positive,1],h[positive,1]=severity_derivatives(y_star[positive],censored[positive],pred[positive,1],structure)
    # Zero rows have exactly zero severity gradient AND curvature.
    # A small floor for active rows is a numerical choice, not a new theorem.
    h[:,0]=np.maximum(h[:,0],1e-10)
    h[positive,1]=np.maximum(h[positive,1],1e-10)
    return g,h


def joint_nll(pred,y_star,occur,censored,structure):
    pred=np.asarray(pred,float).reshape(-1,2)
    loss=np.logaddexp(0,pred[:,0])-occur*pred[:,0]
    positive=occur.astype(bool)
    loss[positive]+=severity_nll(y_star[positive],censored[positive],pred[positive,1],structure)
    return loss


def predict_booster(model,dmatrix):
    return model.predict(dmatrix,output_margin=True,iteration_range=(0,model.best_iteration+1))


def train_joint(X,y,train,valid,test,structure,eta0,params,rounds):
    occur=(y>0).astype(float);t=transform(y,structure);censored=y>=structure.cap
    p0=float(np.mean(occur[train]));zeta0=float(np.log(p0/(1-p0)))
    matrices={}
    for name,idx in [('train',train),('valid',valid),('test',test)]:
        matrices[name]=xgb.DMatrix(X[idx],label=np.column_stack((occur[idx],t[idx])),
                                  base_margin=np.tile([zeta0,eta0],(len(idx),1)))
    def objective(pred,dmatrix):
        labels=dmatrix.get_label().reshape(-1,2)
        # Keep the original administrative flag. Inferring it from rounded
        # float32 transformed labels can misclassify an ordinary near-cap row.
        return joint_derivatives(pred,labels[:,1],labels[:,0],censored[train],structure)
    def metric(pred,dmatrix):
        pred=np.asarray(pred).reshape(-1,2);labels=dmatrix.get_label().reshape(-1,2)
        target=structure.s*labels[:,1]**(1/structure.lam)
        mean=expit(pred[:,0])*bounded_positive_mean(pred[:,1],structure)
        return 'bounded_rmse',float(np.sqrt(np.mean((mean-target)**2)))
    model=xgb.train({**params,'num_target':2,'multi_strategy':'one_output_per_tree',
                     'base_score':0,'disable_default_eval_metric':1},matrices['train'],rounds,
                    obj=objective,custom_metric=metric,evals=[(matrices['valid'],'valid')],
                    early_stopping_rounds=35,verbose_eval=False)
    margin=predict_booster(model,matrices['test']).reshape(-1,2)
    pi=expit(margin[:,0]);conditional=bounded_positive_mean(margin[:,1],structure)
    z=structure.alpha*structure.upper*np.exp(-margin[:,1])
    result={'mean':pi*conditional,'pi':pi,'conditional':conditional,
            'cap_probability':pi*np.exp(gamma_terms(structure.alpha,z)[0]),
            'best_iteration':int(model.best_iteration),'initial_margins':[zeta0,eta0],
            'structure':asdict(structure)}
    return model,result


def synthetic_data(rows,seed,cap,scenario):
    """Two explicit synthetic regimes; neither represents the paper's dataset."""
    rng=np.random.default_rng(seed)
    X=rng.normal(size=(rows,5));X[:,3]=rng.integers(0,2,size=rows)
    pi=expit(-.25+.8*X[:,0]-.55*X[:,1]+.6*X[:,3])
    occurs=rng.random(rows)<pi
    logscale=np.log(3000)+.7*X[:,0]+.5*np.sin(X[:,1])+.25*X[:,2]**2
    if scenario=='lognormal':
        sigma=1.6;catastrophe=.015
        severity=np.exp(logscale+sigma*rng.normal(size=rows))
        severity*=np.where(rng.random(rows)<catastrophe,200,1)
        def capped_lognormal(m):
            return (np.exp(m+sigma*sigma/2)*ndtr((np.log(cap)-m-sigma*sigma)/sigma)
                    +cap*ndtr((m-np.log(cap))/sigma))
        true_conditional=((1-catastrophe)*capped_lognormal(logscale)
                          +catastrophe*capped_lognormal(logscale+np.log(200)))
    else:
        # A model-conforming regime is useful for recovery tests, but favors
        # the model's own family by construction and cannot establish superiority.
        truth=Structure(1000,.3,5,cap)
        mu=(np.exp(logscale)/truth.s)**truth.lam
        severity=truth.s*rng.gamma(truth.alpha,mu/truth.alpha)**(1/truth.lam)
        true_conditional=bounded_positive_mean(np.log(mu),truth)
    raw=np.where(occurs,severity,0)
    return X,np.minimum(raw,cap),raw,pi,true_conditional


def train_baselines(X,y,train,valid,test,s,cap,params,rounds):
    outputs={};models={}
    matrices={name:xgb.DMatrix(X[idx],label=y[idx]/s) for name,idx in [('train',train),('valid',valid),('test',test)]}
    candidate_models=[]
    for p in [1.3,1.5,1.7]:
        model=xgb.train({**params,'objective':'reg:tweedie','tweedie_variance_power':p,'eval_metric':'rmse'},
                        matrices['train'],rounds,evals=[(matrices['valid'],'valid')],early_stopping_rounds=35,verbose_eval=False)
        candidate_models.append((float(model.best_score),p,model))
    _,p,model=min(candidate_models,key=lambda v:v[0])
    limit=(0,model.best_iteration+1)
    mu_scaled=model.predict(matrices['test'],iteration_range=limit)
    valmean=model.predict(matrices['valid'],iteration_range=limit)
    # XGBoost estimates a mean, not full-distribution dispersion. This is a
    # validation-residual MOM diagnostic; it is NOT a Tweedie likelihood MLE.
    phi=float(np.mean((y[valid]/s-valmean)**2/np.maximum(valmean,1e-12)**p))
    diagnostic_pi=-np.expm1(-np.maximum(mu_scaled,1e-12)**(2-p)/(phi*(2-p)))
    bounded=np.minimum(s*mu_scaled,cap)
    outputs['XGBoost Tweedie']={'mean':bounded,'pi':diagnostic_pi,
                              'conditional':None,
                              'cap_probability':None,'power':p,'phi_scaled_diagnostic':phi,
                              'occurrence_kind':'validation-dispersion diagnostic, not a fitted classifier',
                              'best_iteration':int(model.best_iteration)}
    models['tweedie']=model
    occurrence=(y>0).astype(float)
    dm={name:xgb.DMatrix(X[idx],label=occurrence[idx]) for name,idx in [('train',train),('valid',valid),('test',test)]}
    occ=xgb.train({**params,'objective':'binary:logistic','eval_metric':'logloss'},dm['train'],rounds,
                  evals=[(dm['valid'],'valid')],early_stopping_rounds=35,verbose_eval=False)
    pi=occ.predict(dm['test'],iteration_range=(0,occ.best_iteration+1))
    pos_train=train[y[train]>0];pos_valid=valid[y[valid]>0]
    ds=xgb.DMatrix(X[pos_train],label=y[pos_train]/s)
    dv=xgb.DMatrix(X[pos_valid],label=y[pos_valid]/s)
    sev=xgb.train({**params,'objective':'reg:gamma','eval_metric':'rmse'},ds,rounds,
                  evals=[(dv,'valid')],early_stopping_rounds=35,verbose_eval=False)
    conditional=np.minimum(s*sev.predict(xgb.DMatrix(X[test]),iteration_range=(0,sev.best_iteration+1)),cap)
    outputs['Ordinary hurdle Gamma']={'mean':pi*conditional,'pi':pi,'conditional':conditional,'cap_probability':None,
                                       'best_iteration':int(sev.best_iteration),'occurrence_best_iteration':int(occ.best_iteration),'severity_best_iteration':int(sev.best_iteration)}
    models.update(hurdle_occurrence=occ,hurdle_severity=sev)
    return models,outputs


def score(y,pred,high_cut,cap):
    mean=pred['mean'];d=(y>0).astype(float);pi=np.clip(pred['pi'],1e-12,1-1e-12)
    positive=y>0;high=y>=high_cut;boundary=y>=cap
    def rmse(mask):return float(np.sqrt(np.mean((mean[mask]-y[mask])**2))) if mask.any() else None
    bins=np.minimum((pi*10).astype(int),9)
    calibration=[];ece=0.0
    for b in range(10):
        mask=bins==b
        if mask.any():
            gap=abs(float(np.mean(pi[mask])-np.mean(d[mask])))
            ece+=mask.mean()*gap
            calibration.append({'bin':b,'n':int(mask.sum()),'predicted':float(np.mean(pi[mask])),'observed':float(np.mean(d[mask]))})
    result={'rmse':rmse(np.ones(len(y),bool)),'mae':float(np.mean(np.abs(mean-y))),
            'predicted_mean':float(np.mean(mean)),'actual_mean':float(np.mean(y)),
            'occurrence_predicted':float(np.mean(pi)),'occurrence_observed':float(np.mean(d)),
            'occurrence_brier':float(np.mean((pi-d)**2)),
            'occurrence_logloss':float(np.mean(-d*np.log(pi)-(1-d)*np.log1p(-pi))),
            'occurrence_ece_10bins':float(ece),'occurrence_calibration':calibration,
            'severity_predicted_on_observed_positive':float(np.mean(pred['conditional'][positive])) if pred['conditional'] is not None else None,
            'severity_observed_positive':float(np.mean(y[positive])),
            'high_loss_n':int(high.sum()),'high_loss_rmse':rmse(high),
            'high_loss_mean_error':float(np.mean(mean[high]-y[high])) if high.any() else None,
            'capped_n':int(boundary.sum()),'capped_rmse':rmse(boundary),
            'cap_frequency_observed':float(np.mean(boundary)),
            'cap_frequency_predicted':float(np.mean(pred['cap_probability'])) if pred['cap_probability'] is not None else None}
    return result


def self_test():
    """Independent finite differences, integration and counterexamples."""
    tests=[]
    for d in [0.,1.]:
        for zeta in [-3.,0.,2.]:
            eps=1e-4;f=lambda z:np.logaddexp(0,z)-d*z
            pi=expit(zeta)
            np.testing.assert_allclose((f(zeta+eps)-f(zeta-eps))/(2*eps),pi-d,rtol=1e-6,atol=1e-8)
            np.testing.assert_allclose((f(zeta+eps)-2*f(zeta)+f(zeta-eps))/eps**2,pi*(1-pi),rtol=1e-5,atol=1e-7)
    tests.append('logistic finite differences')
    for alpha in [.5,1.,8.,30.]:
        structure=Structure(1000,.25,alpha,100000)
        for censored,z in [(False,3.),(True,.1),(True,1.),(True,10.),(True,100.),(True,2000.)]:
            eta=np.log(alpha*structure.upper/z);t=np.array([structure.upper if censored else .8])
            c=np.array([censored]);eps=1e-4
            f=lambda e:severity_nll(t,c,np.array([e]),structure)[0]
            g,h=severity_derivatives(t,c,np.array([eta]),structure)
            np.testing.assert_allclose((f(eta+eps)-f(eta-eps))/(2*eps),g[0],rtol=1e-5,atol=1e-7)
            np.testing.assert_allclose((f(eta+eps)-2*f(eta)+f(eta-eps))/eps**2,h[0],rtol=2e-3,atol=3e-5)
    tests.append('ordinary and censored Gamma finite differences, including Q underflow')
    z=np.array([10.,100.,1000.,1e6,1e12])
    logq,r,h=gamma_terms(8,z)
    exact_logq=-z+logsumexp(np.array([j*np.log(z)-gammaln(j+1) for j in range(8)]),axis=0)
    np.testing.assert_allclose(logq,exact_logq,rtol=1e-12,atol=1e-10)
    np.testing.assert_allclose(r[-2:]/h[-2:],1,rtol=1e-5)
    tests.append('independent integer-shape survival formula and deep-tail Newton balance')
    structure=Structure(1000,.25,8,100000)
    for eta in [-2.,0.,2.,20.]:
        beta=structure.alpha*np.exp(-eta);z=beta*structure.upper
        # Integrate on unit-rate Gamma coordinates for independent Eq.16 check.
        integral=quad(lambda v:structure.s*(v/beta)**(1/structure.lam)*np.exp((structure.alpha-1)*np.log(v)-v-gammaln(structure.alpha)),0,z,epsabs=1e-7)[0]
        reference=integral+structure.cap*gammaincc(structure.alpha,z)
        np.testing.assert_allclose(bounded_positive_mean([eta],structure)[0],reference,rtol=2e-8,atol=1e-7)
    tests.append('bounded expectation versus numerical integration')
    for eta in [-60.,-20.,0.,20.,60.]:
        m=bounded_positive_mean([eta],structure)[0]
        assert np.isfinite(m) and 0<=m<=structure.cap
    tests.append('original-scale moment stability at extreme means')
    positive=np.array([100.,1000.,10000.,100000.]);c=positive>=structure.cap
    eta=np.full(4,.4);other=Structure(2000,.25,8,100000)
    loss1=severity_nll(transform(positive,structure),c,eta,structure,positive)
    loss2=severity_nll(transform(positive,other),c,eta-.25*np.log(2),other,positive)
    np.testing.assert_allclose(loss1,loss2,rtol=1e-12,atol=1e-12)
    tests.append('scale-anchor invariance with Jacobian and corresponding mean shift')
    a=8.;upper=2.;mu=4.
    paper_boundary=2*(gamma_terms(a,np.array([a]))[0][0]-gamma_terms(a,np.array([a*upper/mu]))[0][0])
    assert paper_boundary<0
    simple=Structure(1,1,a,2)
    g,_=severity_derivatives(np.array([1.,2.]),np.array([False,True]),np.full(2,np.log(1.5)),simple)
    assert abs(g.sum())>.1
    tests.append('counterexamples to nonnegative Eq.21 and censored Eq.34 stationary mean')
    print('SELF-TEST PASS: '+ '; '.join(tests),flush=True)
    return {'checks':tests,'paper_boundary_deviance_counterexample':float(paper_boundary),
            'paper_censored_mean_score_counterexample':float(g.sum())}


def plot_outputs(out,y,predictions,structure):
    try:
        os.environ.setdefault('MPLCONFIGDIR',str(Path(tempfile.gettempdir())/'dutoaa-zig-matplotlib'))
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        warnings.warn('matplotlib unavailable; tabular outputs are complete, SVG plots skipped.');return
    fig,axes=plt.subplots(1,2,figsize=(11,4.2))
    dollars=np.array([100,1000,10000,100000,1000000],float)
    teaching=Structure(1000,.25,8,100000)
    axes[0].plot(dollars,transform(dollars,teaching),'o-',color='#087d70')
    axes[0].set(xscale='log',xlabel='Underlying loss ($, logarithmic axis)',ylabel='Capped transformed value',title='Teaching mapping: s=1,000; lambda=0.25; U=100,000')
    z=np.geomspace(.1,1e5,200);_,r,h=gamma_terms(8,z)
    axes[1].plot(z,r/h,color='#6850ae');axes[1].axhline(1,color='gray',linestyle='--')
    axes[1].set(xscale='log',xlabel='z = alpha U* / mu*',ylabel='Single-observation Newton step',title='Boundary update approaches +1 in the deep tail')
    fig.tight_layout();fig.savefig(out/'transformation-and-newton.svg');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.2))
    for name,pred in predictions.items():
        order=np.argsort(pred['mean']);groups=np.array_split(order,10)
        axes[0].plot([np.mean(pred['mean'][g]) for g in groups],[np.mean(y[g]) for g in groups],'o-',label=name)
        pi=pred['pi'];bins=np.minimum((np.clip(pi,0,1)*10).astype(int),9)
        groups=[np.flatnonzero(bins==i) for i in range(10)];groups=[g for g in groups if len(g)>=10]
        axes[1].plot([np.mean(pi[g]) for g in groups],[np.mean(y[g]>0) for g in groups],'o-',label=name)
    axes[0].set(xlabel='Mean prediction in prediction decile ($)',ylabel='Observed bounded mean ($)',title='Synthetic test mean calibration')
    axes[1].plot([0,1],[0,1],'--',color='gray');axes[1].set(xlabel='Predicted occurrence probability',ylabel='Observed occurrence fraction',title='Tweedie occurrence is a dispersion diagnostic')
    axes[0].legend(fontsize=7);fig.tight_layout();fig.savefig(out/'synthetic-calibration.svg');plt.close(fig)
    # Normalize generated vector text for readable, whitespace-clean version control.
    for path in out.glob('*.svg'):
        path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rows',type=int,default=5000);parser.add_argument('--rounds',type=int,default=250)
    parser.add_argument('--seed',type=int,default=20261003);parser.add_argument('--cap',type=float,default=100000)
    parser.add_argument('--scenario',choices=['lognormal','gamma-power'],default='lognormal')
    parser.add_argument('--lambda-grid',default='.15,.25,.4,.6,.85',help='Training-only structural grid; comma-separated values strictly between 0 and 1')
    parser.add_argument('--output',type=Path,default=Path('research/latent-space-zig/results'))
    parser.add_argument('--self-test',action='store_true');parser.add_argument('--tests-only',action='store_true')
    args=parser.parse_args()
    if args.rows<500 or args.rounds<1 or args.cap<=0:parser.error('Use at least 500 rows, positive cap and rounds.')
    try:
        lambda_grid=[float(value) for value in args.lambda_grid.split(',')]
        if not lambda_grid or not all(0<value<1 for value in lambda_grid):raise ValueError()
    except ValueError:parser.error('--lambda-grid must contain values strictly between 0 and 1.')
    audit=self_test() if args.self_test or args.tests_only else None
    if args.tests_only:return
    X,y,raw,true_pi,true_cond=synthetic_data(args.rows,args.seed,args.cap,args.scenario)
    rng=np.random.default_rng(args.seed+1);idx=rng.permutation(args.rows)
    train,valid,test=np.split(idx,[int(.6*args.rows),int(.8*args.rows)])
    s=float(np.median(y[train][y[train]>0]));s=min(s,args.cap/2)
    structure,eta0,candidates=fit_null_structure(y[train],args.cap,s,lambda_grid)
    control,control_eta,control_candidates=fit_null_structure(y[train],args.cap,s,[1.])
    params={'tree_method':'hist','device':'cpu','max_depth':3,'eta':.05,'lambda':1.,
            'min_child_weight':5.,'max_delta_step':1.,'subsample':.9,'colsample_bytree':1.,
            'seed':args.seed,'nthread':2}
    models,predictions=train_baselines(X,y,train,valid,test,s,args.cap,params,args.rounds)
    for name,key,st,eta in [('Censored hurdle Gamma','censored_hurdle',control,control_eta),
                           ('Latent power-Gamma hurdle','latent',structure,eta0)]:
        model,pred=train_joint(X,y,train,valid,test,st,eta,params,args.rounds)
        models[key]=model;predictions[name]=pred
    high_cut=float(np.quantile(y[train][y[train]>0],.9))
    metrics={name:score(y[test],pred,high_cut,args.cap) for name,pred in predictions.items()}
    versions={'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__,'xgboost':xgb.__version__}
    summary={'notice':'Synthetic demonstration, not a reproduction of the paper, production evidence or a superiority claim.',
             'scenario':args.scenario,'seed':args.seed,'training_parameters':params,'feature_schema':['normal_0','normal_1','normal_2','binary_3','normal_4'],'rows':args.rows,'rounds_limit':args.rounds,
             'split_sizes':{'train':len(train),'validation':len(valid),'test':len(test)},
             'cap':args.cap,'training_anchor':s,'high_loss_threshold_from_training':high_cut,
             'latent_structure':asdict(structure),'latent_profile_candidates':candidates,
             'censored_hurdle_profile':control_candidates,'versions':versions,'self_test':audit,
             'oracle_bounded_mean_rmse':float(np.sqrt(np.mean((true_pi[test]*true_cond[test]-y[test])**2))),
             'model_details':{name:{k:v for k,v in pred.items() if not isinstance(v,np.ndarray)} for name,pred in predictions.items()},
             'metrics':metrics}
    out=args.output;out.mkdir(parents=True,exist_ok=True)
    (out/'metrics.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    fields=['model','rmse','mae','predicted_mean','actual_mean','occurrence_brier','occurrence_ece_10bins',
            'severity_predicted_on_observed_positive','severity_observed_positive','high_loss_rmse','capped_rmse']
    with (out/'comparison.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");writer.writeheader()
        for name,m in metrics.items():writer.writerow({'model':name,**{key:m[key] for key in fields[1:]}})
    with (out/'test-predictions.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator="\n");writer.writerow(['row_id','bounded_response','underlying_response','true_pi','oracle_bounded_mean',*[name for name in predictions]])
        for i,row in enumerate(test):writer.writerow([int(row),float(y[row]),float(raw[row]),float(true_pi[row]),float(true_pi[row]*true_cond[row]),*[float(pred['mean'][i]) for pred in predictions.values()]])
    for key,model in models.items():model.save_model(out/(key+'.ubj'))
    # A joint model also needs structure and base margins at inference time.
    # metrics.json preserves both; the prediction helper always supplies them.
    plot_outputs(out,y[test],predictions,structure)
    print(json.dumps({'versions':versions,'structure':asdict(structure)},indent=2))
    print('\nMODEL                              RMSE       MAE      Predicted mean    Actual mean')
    for name,m in metrics.items():
        print(f'{name:33} {m["rmse"]:10.2f} {m["mae"]:10.2f} {m["predicted_mean"]:15.2f} {m["actual_mean"]:14.2f}')
    print(f'\nOutputs: {out.resolve()}\nNo superiority claim: one synthetic split, selected tuning choices and family-specific assumptions.')


if __name__=='__main__':main()
