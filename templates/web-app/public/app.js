/* Klassiek script: werkt ook wanneer index.html rechtstreeks wordt geopend. */
(() => {
  "use strict";

  function createCounter() {
    let value = 0;
    return {
      value: () => value,
      increment: () => ++value,
      reset: () => (value = 0),
    };
  }

  function mountCounter(document) {
    const output = document.getElementById("count");
    const increment = document.getElementById("increment");
    const reset = document.getElementById("reset");
    if (!output || !increment || !reset) {
      throw new Error("De benodigde tellerelementen ontbreken.");
    }
    const counter = createCounter();
    const render = () => { output.textContent = String(counter.value()); };
    increment.addEventListener("click", () => { counter.increment(); render(); });
    reset.addEventListener("click", () => { counter.reset(); render(); });
    render();
  }

  // Node gebruikt dezelfde code voor tests; de browser initialiseert de pagina.
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { createCounter, mountCounter };
  } else {
    mountCounter(document);
  }
})();
