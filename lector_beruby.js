// Lector de Beruby. Se pega en una pestaña abierta en https://es.beruby.com/ (navegador integrado de la app).
// Lee las fichas https://es.beruby.com/<slug> de /sitemap/main (robots.txt: Crawl-delay 1 s; aquí 1,5 s) y deja en window.__salida:
//   CAMBIOS -> "slug|nombre|variante|pct|nuevos(1/0)|tope|lecturaA|lecturaB" por cada tarifa > 0 de fichas nuevas o con cifras distintas
//   FALLOS  -> slugs publicados cuya ficha ya no cumple la doble lectura (se retiran)
// ANTES de lanzar: window.__publicado = {...}.
// Doble lectura (misma página, dos vías): A = bloques .item-earning del DOM (tipo de compra + porcentaje);
// B = búsqueda de "<span class=\"number ...\">N,NN%</span>" en el HTML crudo. Deben dar las mismas cifras y la ficha
// debe titularse "Cashback en <tienda>". Fichas "no ofrece cashback" o solo con 0 % no generan fila.
// Cuando window.__fin === true el resultado está listo (unos 50-70 minutos).
window.__fin = false; window.__salida = ''; window.__n = 0;
(async () => {
  // Beruby bloquea consultar otros dominios: el mapa de lo publicado se lo pasa quien lanza el lector, en
  // window.__publicado = {slug: [pct, ...]} (sale de cashback.json: filas con plataforma "Beruby").
  const publicado = window.__publicado || {};
  const sm = await (await fetch('/sitemap/main')).text();
  const slugs = [...sm.matchAll(/<loc>https:\/\/es\.beruby\.com\/([a-z0-9-]+)<\/loc>/g)].map(m => m[1])
    .filter(s => !/^(blog|web|sitemap|cashback-novedades|ofertas-en-la-red|compras.*|viajes.*|lo-mas-buscado.*)$/.test(s));
  window.__total = slugs.length;
  const num = s => parseFloat(String(s).replace(',', '.'));
  const cambios = [], vistos = new Set();
  for (const s of slugs) {
    window.__n++;
    try {
      const r = await fetch('/' + s);
      if (r.status === 200) {
        const t = await r.text();
        const d = new DOMParser().parseFromString(t, 'text/html');
        const h1 = ((d.querySelector('h1') || {}).textContent || '').replace(/\s+/g, ' ').trim();
        const m = h1.match(/^Cashback en (.+)$/);
        const tar = [...d.querySelectorAll('.item-earning')].map(e => ({
          tit: ((e.querySelector('.title') || {}).textContent || '').replace(/\s+/g, ' ').trim(),
          num: ((e.querySelector('.number') || {}).textContent || '').trim()
        })).filter(x => x.tit && /^\d+(?:,\d+)?%$/.test(x.num));
        const crudo = [...t.matchAll(/<span class="number[^"]*">\s*(\d+(?:,\d+)?%)\s*<\/span>/g)].map(x => x[1]);
        const coincide = tar.length > 0 && tar.length === crudo.length && tar.every((x, i) => x.num === crudo[i]);
        if (m && coincide) {
          vistos.add(s);
          const pos = tar.filter(x => num(x.num) > 0);
          const sig = pos.map(x => num(x.num)).sort().join(',');
          const antes = (publicado[s] || []).slice().sort().join(',');
          if (pos.length && sig !== antes) {
            const nombre = m[1].replace(/\|/g, '/');
            for (const x of pos) {
              const nuevos = /cliente nuevo|nuevos clientes|primera compra/i.test(x.tit) ? 1 : 0;
              const tope = (x.tit.match(/máximo por transacción:\s*(\d+(?:,\d+)?)\s*€/i) || [])[1] || '';
              const variante = x.tit.replace(/\s*\(.*?\)\s*/g, ' ').replace(/\|/g, '/').trim();
              cambios.push([s, nombre, variante, num(x.num), nuevos, tope ? num(tope) : '', 'Bloque de la ficha: ' + x.tit.replace(/\|/g, '/') + ' ' + x.num, 'HTML de la ficha: ' + x.num].join('|'));
            }
          }
          if (!pos.length && publicado[s]) vistos.delete(s);
        }
      }
    } catch (e) { }
    await new Promise(z => setTimeout(z, 1500));
  }
  const fallos = Object.keys(publicado).filter(s => !vistos.has(s));
  window.__salida = 'CAMBIOS\n' + cambios.join('\n') + '\nFALLOS\n' + fallos.join('\n');
  window.__fin = true;
})();
