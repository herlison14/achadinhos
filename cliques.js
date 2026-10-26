/* Rastreio de cliques do Achadinhos do Binga.
   Os botoes continuam levando direto ao link de afiliado; este script apenas
   avisa o contador em segundo plano. Se o contador falhar, nada muda para o visitante. */
(function () {
  var ENDPOINT = 'https://cliques-binga.herlison14.workers.dev/c';
  if (!ENDPOINT || ENDPOINT.indexOf('SEU-SUBDOMINIO') > -1) return; // ainda nao configurado

  var NOME = /^[a-z0-9_-]{1,20}$/i;

  function origem() {
    var o = '';
    try {
      var q = new URLSearchParams(location.search).get('o');
      if (q && NOME.test(q)) {
        o = q.toLowerCase();
        sessionStorage.setItem('o', o);
      } else {
        o = sessionStorage.getItem('o') || '';
      }
    } catch (e) {}
    return o || 'direto';
  }

  function loja(h) {
    h = h || '';
    return /shopee/.test(h) ? 'shopee' : /amazon/.test(h) ? 'amazon' : /meli\.la|mercadolivre/.test(h) ? 'meli' : /aliexpress/.test(h) ? 'aliexpress' : 'outra';
  }

  var ultimo = { href: '', t: 0 };

  function aoClicar(ev) {
    if (ev.type === 'auxclick' && ev.button !== 1) return;
    var a = ev.target && ev.target.closest ? ev.target.closest('a[rel~="sponsored"]') : null;
    if (!a) return;

    var agora = Date.now();
    if (a.href === ultimo.href && agora - ultimo.t < 1500) return;
    ultimo = { href: a.href, t: agora };

    var nm, cat = '';
    var li = a.closest('li.it');
    if (li) {
      nm = li.querySelector('.nm');
      var h = li.parentNode && li.parentNode.previousElementSibling;
      if (h && h.tagName === 'H2' && h.firstChild) cat = h.firstChild.textContent;
    } else if (a.classList.contains('rc')) {
      nm = a.querySelector('.n');
      cat = 'Menores preços da semana';
    }
    var dados = JSON.stringify({
      p: nm ? nm.textContent : '',
      l: loja(a.href),
      c: cat,
      o: origem(),
    });

    try {
      if (navigator.sendBeacon && navigator.sendBeacon(ENDPOINT, new Blob([dados], { type: 'text/plain;charset=UTF-8' }))) return;
      fetch(ENDPOINT, { method: 'POST', body: dados, keepalive: true, mode: 'no-cors' });
    } catch (e) {}
  }

  document.addEventListener('click', aoClicar, true);
  document.addEventListener('auxclick', aoClicar, true);
})();
