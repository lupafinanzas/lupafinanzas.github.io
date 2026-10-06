// Lector diario de mycashbacks. Se pega en la consola de una pestaña ya abierta en https://www.mycashbacks.com/es/cashbacks/
// (navegador integrado de la app). Lee cada ficha del sitemap a 1 por 1,5 s (robots.txt lo permite; el sitio bloquea
// clientes que no son navegador, por eso se hace desde el navegador). Compara con lo publicado y deja en window.__salida:
//   CAMBIOS  -> líneas "slug|título de la ficha|hasta(1/0)" de fichas nuevas o con cifra distinta (pasan la doble lectura)
//   FALLOS   -> slugs publicados cuya ficha ya no cumple la doble lectura (se retiran)
// Cuando window.__fin === true, el resultado está listo (unos 17 minutos).
window.__fin = false; window.__salida = ''; window.__n = 0;
(async () => {
  const pub = await (await fetch('https://lupafinanzas.github.io/cashback.json')).json();
  const publicado = {};
  for (const t of pub.tiendas) for (const f of t.filas) if (f.plataforma === 'mycashbacks') publicado[t.slug] = f;
  const x = await (await fetch('/es/sitemap/sitemap-0.xml')).text();
  const noTienda = /quienes-somos|condiciones|aviso|privacidad|cashbacks|cupones|promociones|encuestas|guide|asi-funciona|app|finder|milesandmore|legal|contacto|faq|ayuda|blog|cookies|prensa|empleo|user|search|downloads|lead/;
  const EXCL = new Set(['bitpanda', 'coinbase', 'ria']);
  const slugs = [...x.matchAll(/<loc>https:\/\/www\.mycashbacks\.com\/es\/([a-z0-9-]+)\/<\/loc>/g)].map(m => m[1]).filter(s => !noTienda.test(s) && !EXCL.has(s));
  const cambios = [], vistos = new Set();
  for (const s of slugs) {
    window.__n++;
    try {
      const r = await fetch('/es/' + s + '/');
      const t = await r.text();
      const d = new DOMParser().parseFromString(t, 'text/html');
      const main = (d.querySelector('main') || d.body).innerText.replace(/\s+/g, ' ');
      const m1 = main.match(/CASHBACK\s*(Hasta el\s*)?(\d+(?:,\d+)?)\s*%/i);
      const tt = d.title.match(/(\d+(?:,\d+)?)\s*%/);
      const ok = r.status === 200 && r.url.replace(/\/$/, '').endsWith('/es/' + s) && m1 && tt && m1[2] === tt[1];
      if (ok) {
        vistos.add(s);
        const hasta = m1[1] ? 1 : 0, pct = parseFloat(m1[2].replace(',', '.'));
        const p = publicado[s];
        if (!p || p.pct !== pct || (p.hasta_pct ? 1 : 0) !== hasta) cambios.push(s + '|' + d.title.replace(/\|/g, '/') + '|' + hasta);
      }
    } catch (e) { /* ficha no leída: cuenta como fallo si estaba publicada */ }
    await new Promise(z => setTimeout(z, 1500));
  }
  const fallos = Object.keys(publicado).filter(s => !vistos.has(s));
  window.__salida = 'CAMBIOS\n' + cambios.join('\n') + '\nFALLOS\n' + fallos.join('\n');
  window.__fin = true;
})();
