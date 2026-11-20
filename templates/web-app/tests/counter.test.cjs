"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const { createCounter, mountCounter } = require("../public/app.js");

function fakePage() {
  const elements = {};
  for (const id of ["count", "increment", "reset"]) {
    const handlers = {};
    elements[id] = {
      textContent: "",
      addEventListener: (event, handler) => { handlers[event] = handler; },
      click: () => handlers.click(),
    };
  }
  return { elements, getElementById: (id) => elements[id] ?? null };
}

test("de teller begint bij nul en telt op", () => {
  const counter = createCounter();
  assert.equal(counter.value(), 0);
  assert.equal(counter.increment(), 1);
  assert.equal(counter.increment(), 2);
  assert.equal(counter.value(), 2);
});

test("reset werkt ook herhaaldelijk en laat verder tellen toe", () => {
  const counter = createCounter();
  counter.increment();
  assert.equal(counter.reset(), 0);
  assert.equal(counter.reset(), 0);
  assert.equal(counter.increment(), 1);
});

test("tellers hebben ieder hun eigen toestand", () => {
  const first = createCounter();
  const second = createCounter();
  first.increment();
  assert.equal(second.value(), 0);
});

test("knoppen werken de zichtbare teller bij", () => {
  const page = fakePage();
  mountCounter(page);
  assert.equal(page.elements.count.textContent, "0");
  page.elements.increment.click();
  page.elements.increment.click();
  assert.equal(page.elements.count.textContent, "2");
  page.elements.reset.click();
  assert.equal(page.elements.count.textContent, "0");
});

test("ontbrekende elementen geven een duidelijke fout", () => {
  for (const missing of ["count", "increment", "reset"]) {
    const page = fakePage();
    delete page.elements[missing];
    assert.throws(() => mountCounter(page), /tellerelementen ontbreken/);
  }
});

test("het browserscript start zelfstandig zonder Node-globals", () => {
  const page = fakePage();
  const code = fs.readFileSync(path.join(__dirname, "../public/app.js"), "utf8");
  vm.runInNewContext(code, { document: page }, { timeout: 1000 });
  page.elements.increment.click();
  assert.equal(page.elements.count.textContent, "1");
});
