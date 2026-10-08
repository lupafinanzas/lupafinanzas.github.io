/* Lector de BestPrice (ejecutar con javascript_tool en una pestaña de https://bestprice.com/es-es/, p. ej. /es-es/terms).
   Antes: window.__slugs = ["tienda-1", ...].
   Trabaja en segundo plano. Para cada tienda abre https://bestprice.com/es-es/store/<slug> en un marco oculto de la misma web
   (su robots.txt permite /es-es/store/ y sus términos no vetan leer datos; NO se usa /api/, que sí está vetado), espera a que se pinte
   la tarifa y la lee DOS veces con 2,5 s de diferencia. Pausa de 2 s entre tiendas.
   La ficha enseña «[Hasta] X% cashback» (nivel de entrada; el valor sale con prefijo "h" si lleva «Hasta») y «Nivel Negro: Y%» (nivel más alto de su programa de fidelidad).
   Resultado en window.__bp: { fin, n, total, salida: [[slug, X1, niveles1, X2, niveles2]], fallos: [slug...] } */
(function () {
  window.__bp = { fin: false, n: 0, total: window.__slugs.length, salida: [], fallos: [] };
  var pausa = function (ms) { return new Promise(function (ok) { setTimeout(ok, ms); }); };
  var lee = function (doc) {
    var t = (doc.body && doc.body.innerText || "").replace(/\s+/g, " ");
    var b = t.match(/(Hasta\s*)?([\d.,]+)\s*%\s*cashback/i);
    var niv = [], re = /Nivel\s+([A-Za-zÁÉÍÓÚáéíóúñ]+):\s*([\d.,]+)\s*%/g, m;
    while ((m = re.exec(t))) niv.push(m[1] + ":" + m[2]);
    return { base: b ? (b[1] ? "h" : "") + b[2] : null, niveles: niv, titulo: (t.match(/< Volver (.{0,80}?) \d+ visitas/) || [])[1] || "" };
  };
  (async function () {
    for (var i = 0; i < window.__slugs.length; i++) {
      var s = window.__slugs[i];
      var f = document.createElement("iframe");
      f.style.cssText = "position:fixed;left:-9999px;width:420px;height:800px;border:0";
      f.src = "/es-es/store/" + s;
      document.body.appendChild(f);
      var a = null, b = null;
      try {
        for (var k = 0; k < 14; k++) {
          await pausa(1000);
          try { a = lee(f.contentDocument); } catch (e) { a = null; }
          if (a && a.base) break;
        }
        if (a && a.base) { await pausa(2500); b = lee(f.contentDocument); }
      } catch (e) { /* se anota como fallo */ }
      if (a && a.base && b && b.base) window.__bp.salida.push([s, a.base, a.niveles, b.base, b.niveles, a.titulo]);
      else window.__bp.fallos.push(s);
      f.remove();
      window.__bp.n++;
      await pausa(2000);
    }
    window.__bp.fin = true;
  })();
  return "lector iniciado";
})();
