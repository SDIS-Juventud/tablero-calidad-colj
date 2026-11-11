
/* Funciones de pintado que comparten la portada y las paginas internas.
   Los datos llegan por datos/datos_colj.js, que asigna window.DATOS_COLJ.
   Lo genera programas/generar_tablero_calidad_colj.py: no editar a mano. */

var D = window.DATOS_COLJ;

/* Un cuadro por bimestre cerrado, en el orden del calendario. Recibe la lista
   de bimestres que sí tuvieron sesión ordinaria, no cuántos fueron: pintar los
   primeros N cuadros mostraba el bimestre equivocado a las localidades que se
   saltaron uno del medio. */
function bimestres(conOrdinaria, exigidos) {
  var h = '<span class="bimestres">';
  for (var i = 1; i <= exigidos; i++) {
    h += '<i class="' + (conOrdinaria.indexOf(i) >= 0 ? 'si' : 'no') +
         '" title="' + NOMBRE_BIMESTRE[i] + '"></i>';
  }
  return h + '</span>';
}

var NOMBRE_BIMESTRE = {1: 'enero y febrero', 2: 'marzo y abril',
                       3: 'mayo y junio', 4: 'julio y agosto'};

/* Los días que una localidad lleva sin reunirse. Se marca solo cuando pasa el
   umbral de dos meses, para que la columna no se lea como semáforo: todas las
   localidades tienen algún número aquí y eso es normal. */
function silencio(dias) {
  if (dias === null) return '<span class="neutro">sin sesiones</span>';
  var texto = dias + (dias === 1 ? ' día' : ' días');
  if (dias > D.resumen.dias_alerta) {
    return '<span class="pastilla mal">' + texto + '</span>';
  }
  return '<span class="neutro">' + texto + '</span>';
}

function franja(id, casillas) {
  var nodo = document.getElementById(id);
  if (!nodo) return;
  nodo.innerHTML = casillas.map(function (c) {
    return '<div class="casilla">' +
      '<span class="rotulo">' + c.rot + '</span>' +
      '<div class="valor">' + c.v + '</div>' +
      '<div class="glosa">' + c.glosa + '</div></div>';
  }).join('');
}

/* --------------------------------------------------------------- portada */

/* El recordatorio de hasta dónde llegan los datos. Se corre en todas las
   páginas y no hace nada donde no está el nodo.

   Dice las dos cosas a la vez porque ahí está la confusión: la fecha de corte
   es la del último COLJ que quedó registrado, no la del día en que alguien
   abre el tablero. Una tabla puede estar completa aunque la fecha se vea
   vieja, y eso solo se entiende si se dice de dónde sale la fecha. */
function pintarCorte() {
  var nodo = document.getElementById('corte-aviso');
  if (!nodo) return;
  nodo.innerHTML = 'La fecha de corte es el <b>' + D.corte + '</b>: el día ' +
    'en que sesionó el último COLJ registrado.';
}

/* Une los años como se escribe: «2024, 2025 y 2026». */
function listaAnios(anios) {
  if (anios.length < 2) return String(anios[0]);
  return anios.slice(0, -1).join(', ') + ' y ' + anios[anios.length - 1];
}

/* El año abierto es el «año en curso»; uno ya cerrado se nombra por su número. */
function tituloZoom() {
  return D.abierto ? 'Zoom año en curso' : 'Zoom ' + D.anio;
}

function pintarCampos() {
  var r = D.resumen;
  var campos = [
    {href: 'html/estadisticas.html', num: '1', titulo: 'Estadísticas generales',
     glosa: 'Las sesiones de ' + listaAnios(D.anios_serie) +
            ' en las veinte localidades.'},
    {href: 'html/zoom.html', num: '2', titulo: tituloZoom(),
     glosa: 'Cómo va cada localidad en ' + D.anio + '.'},
    {href: 'html/enlaces.html', num: '3',
     titulo: 'Enlaces generales para el análisis de los COLJ', glosa: ''}
  ];
  var nodo = document.getElementById('campos');
  if (!nodo) return;
  nodo.innerHTML = campos.map(function (c) {
    return '<a class="campo" href="' + c.href + '">' +
      '<div class="titulo-campo"><span class="num">' + c.num + '.</span>' +
      c.titulo + '</div>' +
      (c.glosa ? '<div class="glosa-campo">' + c.glosa + '</div>' : '') + '</a>';
  }).join('');
}

/* Una casilla por año. El asterisco marca el año abierto, que todavía
   puede recibir actas; un año cerrado va sin él. */
function pintarFranjaAnios() {
  var t = D.totales_serie;
  var glosas = {2024: 'Año completo, con sesiones mensuales.',
                2025: 'Año completo, ya con sesiones ordinarias bimensuales.'};
  franja('franja-anios', D.anios_serie.map(function (a) {
    var delTablero = a === D.anio;
    return {
      v: t['a' + a] + (delTablero && D.abierto ? '*' : ''),
      rot: 'Actas ' + a,
      glosa: !delTablero ? (glosas[a] || 'Año completo.') :
        (D.abierto ? 'Año en curso' : 'Año completo') +
        ', con corte al ' + D.corte + '.'
    };
  }));
}

function pintarSerie() {
  var anios = D.anios_serie;
  var celdas = function (fila) {
    return anios.map(function (a) {
      return '<td>' + fila['a' + a] + '</td>';
    }).join('');
  };
  var filas = D.serie.map(function (l) {
    return '<tr><td>' + l.localidad + '</td>' + celdas(l) + '</tr>';
  }).join('');
  document.getElementById('tabla-serie').innerHTML = filas +
    '<tr class="total"><td>Total</td>' + celdas(D.totales_serie) + '</tr>';
}

/* Las direcciones se arman dentro de innerHTML, asi que el & de cada
   parametro tiene que ir escapado. Con los enlaces de hoy funciona sin
   escapar, pero es por suerte: si alguna direccion trae &reg=, &not= o
   &para=, el navegador los lee como entidades heredadas y las convierte en
   simbolos. El enlace queda roto y no avisa. */
function escaparUrl(u) {
  return String(u).replace(/&/g, '&amp;').replace(/"/g, '%22');
}

function pintarEnlaces() {
  var nodo = document.getElementById('enlaces');
  if (!nodo) return;
  nodo.innerHTML = D.enlaces.map(function (e) {
    var cuerpo = '<div class="nombre-enlace">' + e.nombre + '</div>' +
      '<div class="glosa">' + e.glosa + '</div>';
    if (e.url) {
      return '<a class="enlace" href="' + escaparUrl(e.url) + '" target="_blank" ' +
        'rel="noopener">' + cuerpo +
        '<span class="ir">Abrir &rarr;</span></a>';
    }
    return '<div class="enlace">' + cuerpo +
      '<span class="marca-pendiente">Dirección por definir</span></div>';
  }).join('');
}

function pintarPanorama() {
  var r = D.resumen;
  franja('franja-general', [
    {v: r.sesiones_formulario, rot: 'Sesiones realizadas',
     glosa: r.ordinarias + ' ordinarias y ' + r.extraordinarias +
            ' extraordinarias en las 20 localidades.'},
    {v: r.actas, rot: 'Sesiones con acta',
     glosa: 'De ' + r.sesiones_formulario + ' reportadas al formulario.'},
    {v: r.al_dia_sesiones + ' de 20', rot: 'Localidades al día en sesiones',
     glosa: 'Hicieron las ' + r.ordinarias_exigidas +
            ' sesiones ordinarias que se esperan al corte.'},
    {v: r.sin_pendientes + ' de 20', rot: 'Localidades sin nada pendiente',
     glosa: 'Sesionaron, cargaron todo y no tienen ajustes de forma.'}
  ]);
}

/* ------------------------------------------------------- paginas internas */

function pintarPeriodicidad() {
  var filas = D.localidades.map(function (l) {
    return '<tr>' +
      '<td>' + l.localidad + '</td>' +
      '<td>' + bimestres(l.bimestres_con_ordinaria, l.bimestres_exigidos) +
      '</td>' +
      '<td>' + (l.faltan_ordinarias
                ? '<span class="pastilla mal">' + l.ordinarias + ' de ' +
                  l.ordinarias_exigidas + '</span>'
                : '<span class="neutro">' + l.ordinarias + '</span>') +
      '</td>' +
      '<td>' + l.extraordinarias + '</td>' +
      '<td>' + l.sesiones_formulario + '</td>' +
      '<td>' + silencio(l.dias_sin_sesionar) + '</td></tr>';
  }).join('');
  var r = D.resumen;
  document.getElementById('tabla-periodicidad').innerHTML = filas +
    '<tr class="total"><td>Total</td><td></td>' +
    '<td>' + r.ordinarias + '</td>' +
    '<td>' + r.extraordinarias + '</td>' +
    '<td>' + r.sesiones_formulario + '</td>' +
    '<td></td></tr>';

  // El conteo de localidades en silencio va en la leyenda y no en la fila de
  // total: esa fila suma columnas y una frase ahí rompe la lectura.
  var aviso = document.getElementById('resumen-silencio');
  if (aviso) {
    aviso.innerHTML = r.en_silencio
      ? 'Al corte, ' + r.en_silencio + (r.en_silencio === 1 ? ' localidad.' : ' localidades.')
      : 'Al corte, ninguna.';
  }
}

/* Formato colombiano: miles con punto. Si algún día hace falta un decimal,
   va con coma. */
function miles(n) {
  var s = String(n), salida = '';
  while (s.length > 3) {
    salida = '.' + s.slice(-3) + salida;
    s = s.slice(0, -3);
  }
  return s + salida;
}
function mayuscula(t) { return t.charAt(0).toUpperCase() + t.slice(1); }
/* "Bosa, Usme y Sumapaz" */
function enumerar(lista) {
  if (lista.length < 2) return lista.join('');
  return lista.slice(0, -1).join(', ') + ' y ' + lista[lista.length - 1];
}

/* Consulta bajo la tabla de periodicidad. Responde dos preguntas: qué
   sesiones tuvo una localidad, cuándo y con cuántos asistentes, y cuántos
   COLJ hubo en un rango de meses y en qué localidades. */
function pintarConsulta() {
  var selLoc = document.getElementById('filtro-localidad');
  if (!selLoc) return;
  var selDesde = document.getElementById('filtro-desde');
  var selHasta = document.getElementById('filtro-hasta');
  var selOrden = document.getElementById('filtro-orden');
  var quitar = document.getElementById('quitar-filtros');
  var tabla = document.getElementById('tabla-consulta');
  var M = D.meses;
  var nombres = M.nombres_consulta;
  // En la consulta las localidades van en orden alfabético, en la lista y en
  // la tabla, porque así se buscan. Con el orden oficial de las 20 no se
  // encontraba Los Mártires sin recorrer la lista entera.
  var todas = D.localidades.map(function (l) { return l.localidad; })
    .sort(function (a, b) { return a.localeCompare(b, 'es'); });

  selLoc.innerHTML = '<option value="">Todas</option>' +
    todas.map(function (l) { return '<option>' + l + '</option>'; }).join('');
  var opciones = nombres.map(function (n, i) {
    return '<option value="' + (i + 1) + '">' + mayuscula(n) + '</option>';
  }).join('');
  selDesde.innerHTML = opciones;
  selHasta.innerHTML = opciones;
  // La tabla se ordena de dos maneras que comparten el mismo estado: con la
  // lista "Ordenar por" o con un clic en el título de una columna (el segundo
  // clic invierte el orden). Todo orden que se puede pedir en la tabla está
  // también en la lista, para quien no sepa que los títulos se pueden tocar,
  // y cada forma refleja lo que hizo la otra. "Quitar filtros" las devuelve
  // a localidad de la A a la Z. Los nombres, el número de sesión y las fechas
  // arrancan de menor a mayor y las cifras de mayor a menor, que es lo que se
  // busca.
  var COLUMNAS = [
    {id: 'localidad', rot: 'Localidad', asc: 'A a Z', desc: 'Z a A'},
    {id: 'numero', rot: 'Sesión', corto: 'N.º', asc: 'primera a última',
     desc: 'última a primera'},
    {id: 'fecha', rot: 'Fecha', asc: 'más antigua primero',
     desc: 'más reciente primero'},
    {id: 'tipo', rot: 'Tipo', asc: 'ordinarias primero',
     desc: 'extraordinarias primero'},
    {id: 'asistencias', rot: 'Asistentes', corto: 'Asist.', cifra: true,
     asc: 'de menos a más', desc: 'de más a menos'},
    {id: 'jovenes', rot: 'Jóvenes', corto: 'Jóv.', cifra: true,
     asc: 'de menos a más', desc: 'de más a menos'}
  ];
  // En la lista, las opciones siguen el orden de las columnas, y en cada
  // columna va primero el sentido con que arranca al hacer clic
  selOrden.innerHTML = COLUMNAS.map(function (c) {
    var sentidos = c.cifra ? ['desc', 'asc'] : ['asc', 'desc'];
    return sentidos.map(function (s) {
      return '<option value="' + c.id + '-' + s + '">' + c.rot + ' (' + c[s] +
        ')</option>';
    }).join('');
  }).join('');
  function esCifra(id) {
    return COLUMNAS.some(function (c) { return c.id === id && c.cifra; });
  }
  var RANGO_TIPO = {'Ordinaria': 0, 'Extraordinaria': 1};
  var TIPO_CORTO = {'Ordinaria': 'Ord.', 'Extraordinaria': 'Extra.'};
  // Un texto con su versión para pantallas pequeñas. Sin versión corta, queda igual
  function conCorto(largo, corto) {
    return corto ? '<span class="largo">' + largo + '</span>' +
      '<span class="corto">' + corto + '</span>' : largo;
  }
  function comparar(id, a, b) {
    if (id === 'localidad') return a.localidad.localeCompare(b.localidad, 'es');
    if (id === 'tipo') return (RANGO_TIPO[a.tipo] === undefined ? 2 : RANGO_TIPO[a.tipo]) -
      (RANGO_TIPO[b.tipo] === undefined ? 2 : RANGO_TIPO[b.tipo]);
    if (id === 'fecha') return (a.mes * 100 + a.dia) - (b.mes * 100 + b.dia);
    return a[id] - b[id];
  }
  // Las flechas de los títulos se dibujan en SVG y no con caracteres: el
  // iPhone pinta la flecha doble como un emoji de cuadrito azul, y cada
  // teléfono dibuja las flechas de texto a su manera. Con un trazo propio
  // las tres se ven iguales en cualquier pantalla.
  var TRAZOS_FLECHA = {
    asc: 'M4 11V1.5M1 4.5l3-3 3 3',
    desc: 'M4 1v9.5M1 7.5l3 3 3-3',
    ambas: 'M4 1.5v9M1.5 4l2.5-2.5L6.5 4M1.5 8l2.5 2.5L6.5 8'
  };
  function flechaOrden(sentido) {
    return '<svg class="flecha" viewBox="0 0 8 12" aria-hidden="true">' +
      '<path d="' + TRAZOS_FLECHA[sentido] + '" fill="none"' +
      ' stroke="currentColor" stroke-width="1.5" stroke-linecap="round"' +
      ' stroke-linejoin="round"/></svg>';
  }
  var orden;

  function valoresIniciales() {
    selLoc.value = '';
    selDesde.value = '1';
    selHasta.value = String(nombres.length);
    orden = {id: 'localidad', asc: true};
  }

  function actualizar(cambio) {
    var desde = +selDesde.value, hasta = +selHasta.value;
    // Si el rango queda al revés, se mueve el extremo que no se tocó
    if (desde > hasta) {
      if (cambio === selHasta) { desde = hasta; selDesde.value = desde; }
      else { hasta = desde; selHasta.value = hasta; }
    }
    var loc = selLoc.value;
    var lista = M.sesiones.filter(function (s) {
      return s.mes >= desde && s.mes <= hasta && (!loc || s.localidad === loc);
    });

    var tA = 0, tJ = 0, conSesion = {};
    lista.forEach(function (s) {
      tA += s.asistencias; tJ += s.jovenes; conSesion[s.localidad] = true;
    });
    var n = lista.length;
    var periodo = desde === hasta ? 'en ' + nombres[desde - 1]
      : 'de ' + nombres[desde - 1] + ' a ' + nombres[hasta - 1];
    var sesiones = '<b>' + n + (n === 1 ? ' sesión' : ' sesiones') + '</b>';
    // Promedio por sesión y no total: el total sumaba participaciones y se
    // leía como personas distintas. Va redondeado a entero porque cuenta
    // personas. Con una sola sesión van sus cifras.
    var pA = n ? Math.round(tA / n) : 0, pJ = n ? Math.round(tJ / n) : 0;
    var deJovenes = pJ ? pJ + (pJ === 1 ? ' de ellos joven.' : ' de ellos jóvenes.')
      : (tJ ? 'menos de uno de ellos joven.' : 'ninguno joven.');
    var cifras = n === 1
      ? ', con ' + tA + ' asistentes, ' + deJovenes
      : ', con un promedio de ' + pA + ' asistentes por sesión, ' + deJovenes;
    var texto;
    if (loc) {
      texto = n ? loc + ' tuvo ' + sesiones + ' ' + periodo + cifras
                : loc + ' no tuvo sesiones ' + periodo + '.';
    } else if (!n) {
      texto = mayuscula(periodo) + ' no hubo sesiones.';
    } else {
      var nLoc = Object.keys(conSesion).length;
      var faltan = todas.filter(function (l) { return !conSesion[l]; });
      texto = mayuscula(periodo) + ' hubo ' + sesiones + ' en <b>' + nLoc +
        (nLoc === 1 ? ' localidad' : ' localidades') + '</b>' + cifras +
        '<span class="sin-sesion">' + (faltan.length
          ? 'Sin sesión en ese periodo: ' + enumerar(faltan) + '.'
          : 'Las ' + todas.length + ' localidades sesionaron en ese periodo.') +
        '</span>';
    }
    document.getElementById('resumen-consulta').innerHTML = texto;

    // Orden: si se tocó la lista, manda la lista; después la lista muestra
    // el orden vigente, venga de donde venga
    if (cambio === selOrden) {
      var partes = selOrden.value.split('-');
      orden = {id: partes[0], asc: partes[1] === 'asc'};
    }
    selOrden.value = orden.id + '-' + (orden.asc ? 'asc' : 'desc');

    // El botón de quitar filtros solo aparece si algo cambió: así se sabe de
    // un vistazo si la tabla está completa o filtrada
    var cambiado = loc || desde !== 1 || hasta !== nombres.length ||
      orden.id !== 'localidad' || !orden.asc;
    quitar.style.visibility = cambiado ? 'visible' : 'hidden';

    // Con una sola localidad elegida, la columna de localidad sobra
    var conLoc = !loc;
    lista.sort(function (a, b) {
      var d = comparar(orden.id, a, b);
      if (!orden.asc) d = -d;
      // Los empates se resuelven por localidad y fecha
      return d || comparar('localidad', a, b) || comparar('fecha', a, b);
    });
    var cab = COLUMNAS.filter(function (c) {
      return conLoc || c.id !== 'localidad';
    }).map(function (c) {
      var activa = c.id === orden.id;
      var flecha = flechaOrden(activa ? (orden.asc ? 'asc' : 'desc') : 'ambas');
      return '<th' + (activa ? ' aria-sort="' +
          (orden.asc ? 'ascending' : 'descending') + '"' : '') + '>' +
        '<button type="button" class="ordenar' + (activa ? ' activa' : '') +
        '" data-col="' + c.id + '" aria-label="' + c.rot + '">' +
        conCorto(c.rot, c.corto) + flecha + '</button></th>';
    }).join('');
    var filas = lista.map(function (s) {
      return '<tr>' + (conLoc ? '<td>' + s.localidad + '</td>' : '') +
        '<td>' + s.numero + '</td>' +
        '<td class="sin-corte">' + s.dia +
        conCorto(' de ' + nombres[s.mes - 1], ' ' + nombres[s.mes - 1].slice(0, 3)) +
        '</td>' +
        '<td class="sin-corte">' + conCorto(s.tipo, TIPO_CORTO[s.tipo]) + '</td>' +
        '<td>' + miles(s.asistencias) + '</td>' +
        '<td>' + miles(s.jovenes) + '</td></tr>';
    }).join('');
    tabla.className = conLoc ? '' : 'una-localidad';
    tabla.innerHTML = '<thead><tr>' + cab + '</tr></thead><tbody>' + filas +
      '<tr class="total"><td>Promedio</td>' + (conLoc ? '<td></td>' : '') +
      '<td></td><td></td><td>' + (n ? pA : '') + '</td>' +
      '<td>' + (n ? pJ : '') + '</td></tr>' +
      '</tbody>';
    tabla.parentNode.style.display = n ? '' : 'none';
  }

  [selLoc, selDesde, selHasta, selOrden].forEach(function (s) {
    s.addEventListener('change', function () { actualizar(s); });
  });
  tabla.addEventListener('click', function (e) {
    var boton = e.target.closest('button.ordenar');
    if (!boton) return;
    var id = boton.getAttribute('data-col');
    orden = orden.id === id ? {id: id, asc: !orden.asc}
                            : {id: id, asc: !esCifra(id)};
    actualizar(null);
    // La tabla se vuelve a pintar: el foco vuelve al mismo título para quien
    // ordena con el teclado
    var nuevo = tabla.querySelector('button[data-col="' + id + '"]');
    if (nuevo) nuevo.focus();
  });
  quitar.addEventListener('click', function () {
    valoresIniciales();
    actualizar(null);
  });
  valoresIniciales();
  actualizar(null);
}

