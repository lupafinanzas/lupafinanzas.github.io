/* Lector de iGraal (ejecutar con javascript_tool en una pestaña de https://es.igraal.com/, p. ej. /robots.txt).
   Antes: window.__slugs = ["tienda-1","tienda-2",...].
   Trabaja en segundo plano: lee https://es.igraal.com/codigos-promocionales/<slug> (robots.txt lo permite), con 2 s de pausa.
   De cada ficha guarda en bruto: título de la página, los títulos de tarjeta («offerbasecard-title») y los textos «… de cashback».
   La interpretación y la doble lectura las hace importar_igraal.py. Resultado en window.__ig (fin, n, salida, fallos). */
(function () {
  window.__ig = { fin: false, n: 0, total: (window.__slugs || []).length, salida: [], fallos: [] };
  var limpia = function (s) { return (s || "").replace(/[⁠​ ]/g, " ").replace(/\s+/g, " ").trim(); };
  (async function () {
    for (var i = 0; i < window.__slugs.length; i++) {
      var s = window.__slugs[i];
      try {
        var r = await fetch("/codigos-promocionales/" + s, { credentials: "omit" });
        if (r.status !== 200) { window.__ig.fallos.push(s + "|" + r.status); }
        else {
          var h = await r.text();
          var t = limpia((h.match(/<title>([^<]*)<\/title>/) || [])[1]);
          var tarjetas = [];
          var re1 = /id="offerbasecard-title"[^>]*>([^<]*)</g, m;
          while ((m = re1.exec(h)) && tarjetas.length < 4) tarjetas.push(limpia(m[1]));
          var textos = [];
          var re2 = /<span class="[^"]*">([^<]*de cashback[^<]*)<\/span>/g;
          while ((m = re2.exec(h)) && textos.length < 3) textos.push(limpia(m[1]));
          window.__ig.salida.push([s, t, tarjetas, textos]);
        }
      } catch (e) { window.__ig.fallos.push(s + "|err"); }
      window.__ig.n++;
      await new Promise(function (ok) { setTimeout(ok, 2000); });
    }
    window.__ig.fin = true;
  })();
  return "lector iniciado";
})();
