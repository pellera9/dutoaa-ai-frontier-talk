// Mermaid is an optional enhancement. Documents and offline SVG flows remain readable without it.
let mermaidPromise;
let renderCount = 0;
document.querySelectorAll('.render-mermaid').forEach(button => {
  button.addEventListener('click', async () => {
    button.disabled = true;
    button.textContent = 'Loading Mermaid…';
    try {
      mermaidPromise ??= import('https://cdn.jsdelivr.net/npm/mermaid@11.12.0/dist/mermaid.esm.min.mjs').then(module => {
        module.default.initialize({startOnLoad:false, securityLevel:'strict', theme:'default'});
        return module.default;
      }).catch(error => { mermaidPromise = undefined; throw error; });
      const mermaid = await mermaidPromise;
      const wrapper = button.closest('.mermaid-source');
      const result = await mermaid.render(`mermaid-${++renderCount}`, wrapper.querySelector('code').textContent);
      wrapper.querySelector('.mermaid-output').innerHTML = result.svg;
      button.textContent = 'Diagram rendered';
    } catch {
      button.textContent = 'Rendering unavailable — retry or use Mermaid source';
      button.disabled = false;
    }
  });
});

// Equations remain as copyable LaTeX offline; MathJax is an explicit optional enhancement.
document.querySelectorAll('.render-math').forEach(button => {
  button.addEventListener('click', async () => {
    button.disabled = true;
    button.textContent = 'Loading equations…';
    try {
      if (!window.MathJax?.typesetPromise) {
        window.MathJax = {tex: {inlineMath: [['$', '$'], ['\\(', '\\)']], displayMath: [['$$', '$$'], ['\\[', '\\]']], processEscapes: true}, startup: {typeset: false}};
        await new Promise((resolve, reject) => {
          const script = document.createElement('script');
          script.src = 'https://cdn.jsdelivr.net/npm/mathjax@4.0.0/tex-chtml.js';
          script.onload = resolve;
          script.onerror = () => {script.remove(); reject(new Error('Equation renderer unavailable'));};
          document.head.append(script);
        });
        await window.MathJax.startup.promise;
      }
      await window.MathJax.typesetPromise([document.getElementById('document')]);
      button.textContent = 'Equations rendered';
    } catch {
      button.textContent = 'Rendering unavailable — retry or read LaTeX source';
      button.disabled = false;
    }
  });
});
