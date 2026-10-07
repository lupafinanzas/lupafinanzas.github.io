// Lector de Widilo. Se pega en una pestaña abierta en https://www.widilo.es/ (navegador integrado de la app).
// Lee las fichas https://www.widilo.es/codigo-descuento/<slug> del shop-sitemap (robots.txt lo permite) a 1 cada 1,5 s.
// Doble lectura de cada cifra: (A) título o meta descripción de la ficha ("3,9% Cashback", "hasta 3,6% de cashback")
// y (B) los datos de la ficha (bloque ng-state: cashbackRate/cashbackValue). Solo se acepta si A y B coinciden,
// es cashback en % (cashbackType 1), sin tarifas múltiples. Compara con lo publicado y deja en window.__salida:
//   CAMBIOS -> "slug|nombre|pct|subida(1/0)|habitual|lecturaA|lecturaB" de fichas nuevas o con cifra distinta
//   FALLOS  -> slugs publicados cuya ficha ya no cumple la doble lectura (se retiran)
// Cuando window.__fin === true el resultado está listo (unos 23 minutos).
window.__fin = false; window.__salida = ''; window.__n = 0;
(async () => {
  const pub = await (await fetch('https://lupafinanzas.github.io/cashback.json?x=' + Date.now())).json();
  const publicado = {};
  for (const t of pub.tiendas) for (const f of t.filas) if (f.plataforma === 'Widilo') publicado[t.slug] = f;
  const sm = await (await fetch('/shop-sitemap.xml')).text();
  const slugs = [...sm.matchAll(/<loc>https:\/\/www\.widilo\.es\/codigo-descuento\/([a-z0-9-]+)<\/loc>/g)].map(m => m[1]);
  const re = /(\d+(?:,\d+)?)\s?%\s*(?:de\s*)?cashback/i;
  const num = s => parseFloat(String(s).replace(',', '.'));
  const cambios = [], vistos = new Set();
  for (const s of slugs) {
    window.__n++;
    try {
      const r = await fetch('/codigo-descuento/' + s);
      if (r.status === 200) {
        const d = new DOMParser().parseFromString(await r.text(), 'text/html');
        const el = d.getElementById('ng-state');
        let main = null;
        (function walk(x, p, dep) {
          if (main || dep > 9 || x === null) return;
          if (typeof x === 'string') { if (/^\{/.test(x) && x.length > 50) { try { walk(JSON.parse(x), p + '~', dep + 1); } catch (e) {} } return; }
          if (typeof x !== 'object') return;
          if ('cashbackRate' in x && 'metaTitle' in x && !/similarShops|\.shops\./.test(p)) { main = x; return; }
          for (const k in x) walk(x[k], p + '.' + k, dep + 1);
        })(el ? JSON.parse(el.textContent) : null, '', 0);
        const desc = (d.querySelector('meta[name=description]') || {}).content || '';
        const a = d.title.match(re) || desc.match(re);
        if (main && a && main.isCashback === true && main.cashbackType === 1 && !main.hasMultipleCashbackValue &&
            main.cashbackRate > 0 && main.cashbackRate <= 100 && num(a[1]) === main.cashbackRate) {
          const nombre = ((main.deals && main.deals[0] && main.deals[0].shopName) || (d.querySelector('h1') || {}).innerText || '').replace(/^\s*Código descuento\s*|\s+y cashback.*$/gi, '').replace(/\|/g, '/').trim();
          if (nombre) {
            vistos.add(s);
            const inc = main.cashbackIsIncrease && main.cashbackBeforeIncreaseValue ? 1 : 0;
            const hab = inc ? num(main.cashbackBeforeIncreaseValue) : main.cashbackRate;
            const p = publicado[s];
            if (!p || p.pct !== main.cashbackRate || (p.tipo === 'aumentado' ? 1 : 0) !== inc)
              cambios.push([s, nombre, main.cashbackRate, inc, hab, a[0].replace(/\|/g, '/'), main.cashbackValue + (inc ? ' (antes ' + main.cashbackBeforeIncreaseValue + ')' : '')].join('|'));
          }
        }
      }
    } catch (e) { /* ficha no leída */ }
    await new Promise(z => setTimeout(z, 1500));
  }
  const fallos = Object.keys(publicado).filter(s => !vistos.has(s));
  window.__salida = 'CAMBIOS\n' + cambios.join('\n') + '\nFALLOS\n' + fallos.join('\n');
  window.__fin = true;
})();
