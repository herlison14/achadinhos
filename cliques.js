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

  var AWD = {'kabum.com.br': 'kabum', 'nike.com.br': 'nike', 'dafiti.com.br': 'dafiti', 'adidas.com.br': 'adidas', 'docebeleza.com.br': 'docebeleza', 'br.puma.com': 'puma', 'hopelingerie.com.br': 'hope', 'hopeoficial.com.br': 'hope', 'mizuno.com.br': 'mizuno', 'polishop.com.br': 'polishop'};
  function loja(h) {
    h = h || '';
    if (/awin1\.com\//.test(h)) {
      var u = '';
      try { u = decodeURIComponent((h.match(/[?&]ued=([^&]+)/) || [])[1] || ''); } catch (e) {}
      var hs = ((u.match(/^https?:\/\/([^\/?#]+)/) || [])[1] || '').replace(/^www\./, '');
      for (var d in AWD) { if (hs === d || hs.slice(-d.length - 1) === '.' + d) return AWD[d]; }
      return 'outra';
    }
    return /magazinevoce/.test(h) ? 'magalu' : /shopee/.test(h) ? 'shopee' : /amazon/.test(h) ? 'amazon' : /meli\.la|mercadolivre/.test(h) ? 'meli' : /aliexpress/.test(h) ? 'aliexpress' : 'outra';
  }

  function categoriaDe(li) {
    var h = li && li.parentNode && li.parentNode.previousElementSibling;
    return h && h.tagName === 'H2' && h.firstChild ? h.firstChild.textContent : '';
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
      cat = categoriaDe(li);
    } else if (a.classList.contains('rc')) {
      nm = a.querySelector('.n');
      // O trilho "Menores preços" repete itens da lista: usa a categoria real do item
      cat = 'Menores preços da semana';
      if (nm) {
        var nomes = document.querySelectorAll('li.it .nm');
        for (var i = 0; i < nomes.length; i++) {
          if (nomes[i].textContent === nm.textContent) { cat = categoriaDe(nomes[i].closest('li.it')) || cat; break; }
        }
      }
    }
    if (!nm && a.getAttribute('data-p')) {
      // botões da busca sem resultado (lojas e "parecidos")
      nm = { textContent: a.getAttribute('data-p').slice(0, 120) };
      cat = a.getAttribute('data-c') || cat;
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
