/* Votos «Me funcionó» / «No me funcionó» de los códigos, con GoatCounter (sin cookies).
   Cada voto es un evento funciona-<id> o nofunciona-<id>; los contadores se leen de la API pública de contadores. */
(function(){
  var BASE='https://lupafinanzas.goatcounter.com/';
  function el(t,c,x){var e=document.createElement(t);if(c)e.className=c;if(x!==undefined)e.textContent=x;return e;}
  function guardado(id){try{return localStorage.getItem('voto_'+id);}catch(e){return null;}}
  function guarda(id,v){try{localStorage.setItem('voto_'+id,v);}catch(e){}}
  function leer(ev){
    return fetch(BASE+'counter/'+encodeURIComponent(ev)+'.json').then(function(r){return r.ok?r.json():{count:'0'};}).then(function(j){return parseInt(String(j.count).replace(/\D/g,''),10)||0;}).catch(function(){return 0;});
  }
  var obs=('IntersectionObserver' in window)?new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){obs.unobserve(e.target);e.target._carga();}});},{rootMargin:'200px'}):null;
  window.Votos={
    crear:function(id,tienda){
      var box=el('div','votos'),n={s:0,n:0},previo=guardado(id);
      box.appendChild(el('span','votos-q','¿Te funcionó este código?'));
      var bs=el('button','votos-b','Me funcionó'),bn=el('button','votos-b','No me funcionó');
      bs.type=bn.type='button';
      var cs=el('span','votos-n',''),cn=el('span','votos-n','');bs.appendChild(cs);bn.appendChild(cn);
      function pinta(){
        cs.textContent=n.s?' ('+n.s+')':'';cn.textContent=n.n?' ('+n.n+')':'';
        var v=guardado(id);if(v){bs.disabled=bn.disabled=true;(v==='s'?bs:bn).classList.add('votado');}
      }
      function vota(v){
        if(guardado(id))return;
        guarda(id,v);
        if(v==='s')n.s++;else n.n++;
        try{if(window.goatcounter&&window.goatcounter.count)window.goatcounter.count({path:(v==='s'?'funciona-':'nofunciona-')+id,title:'Voto '+(v==='s'?'funciona':'no funciona')+' · '+tienda,event:true});}catch(e){}
        pinta();
      }
      bs.addEventListener('click',function(){vota('s');});bn.addEventListener('click',function(){vota('n');});
      box.appendChild(bs);box.appendChild(bn);
      box.appendChild(el('span','votos-aviso','Votos de visitantes, sin verificar; tardan unos minutos en aparecer.'));
      box._carga=function(){Promise.all([leer('funciona-'+id),leer('nofunciona-'+id)]).then(function(r){n.s=r[0]+(previo==='s'&&!r[0]?1:0);n.n=r[1]+(previo==='n'&&!r[1]?1:0);pinta();});};
      pinta();
      if(obs)obs.observe(box);else box._carga();
      return box;
    }
  };
})();
