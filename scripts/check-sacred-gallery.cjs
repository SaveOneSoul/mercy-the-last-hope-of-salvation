#!/usr/bin/env node
// Static regression checks; browser accessibility requires a separate manual/axe audit.
const fs=require('node:fs'),assert=require('node:assert/strict');
const html=fs.readFileSync('pages/gallery.html','utf8');
function extract(name,terminator){const start=html.indexOf('const '+name+'=');assert(start>=0,'Missing '+name);const a=start+('const '+name+'=').length;const b=html.indexOf(terminator,a);assert(b>a,'Malformed '+name);return JSON.parse(html.slice(a,b))}
const sections=extract('sections',';\n// Only approved');
const notes=extract('marianNotes',';\nconst viewer=');
const marian=sections.find(s=>s.name==='Marian Gallery');
assert(marian,'Missing Marian Gallery');
assert.equal(marian.items.length,54);
assert.equal(new Set(marian.items).size,54);
assert.equal(Object.keys(notes).length,54);
for(const title of marian.items){const n=notes[title];assert(n,'Missing note: '+title);for(const field of ['meaning','scripture','history'])assert(n[field]?.trim(),'Missing '+field+' for '+title)}
for(const [previous,title] of [['Mother of the Church','Mother of Mercy'],['Mother of divine grace','Mother of Hope'],['Refuge of sinners','Solace of Migrants']])assert.equal(marian.items.indexOf(title),marian.items.indexOf(previous)+1);
assert(html.includes('aria-labelledby="viewer-title"'));
assert(html.includes('aria-live="polite"'));
assert(html.includes('previousFocus.focus()'));
assert(html.includes("search.addEventListener('input',draw)"));
assert(html.includes("details.addEventListener('click'"));
assert(html.includes("const approvedArt="));
console.log('PASS: 54 Marian titles, notes, Vatican additions, basic gallery controls and dialog hooks.');
console.log('NOT TESTED: image HTTP responses, screen readers, browser focus trap, color contrast, responsive layout.');
