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
