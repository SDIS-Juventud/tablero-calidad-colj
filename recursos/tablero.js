
/* Funciones de pintado que comparten la portada y las paginas internas.
   Los datos llegan por datos/datos_colj.js, que asigna window.DATOS_COLJ.
   Lo genera programas/generar_tablero_calidad_colj.py: no editar a mano. */

var D = window.DATOS_COLJ;

function pastilla(valor) {
  if (valor === 0) return '<span class="neutro">0</span>';
  return '<span class="pastilla mal">' + valor + '</span>';
}

function fraccion(parte, total) {
  if (parte === total) {
    return '<span class="neutro">' + parte + ' de ' + total + '</span>';
  }
  return '<span class="pastilla mal">' + parte + ' de ' + total + '</span>';
}

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

function barra(bien, total) {
  if (!total) return '';
  var p = function (n) { return (n / total * 100).toFixed(1); };
  return '<div class="barra">' +
    '<span class="b-bien" style="width:' + p(bien) + '%"></span>' +
    '<span class="b-mal" style="width:' + p(total - bien) + '%"></span></div>';
}

var ETIQUETA_ESTADO = {
  'al día': ['al-dia', 'Al día'],
  'revisar forma': ['revisar', 'Ajustes de forma'],
  'falta cargar': ['cargar', 'Por cargar'],
  'falta sesionar': ['sesionar', 'Por sesionar']
};

function chip(estado) {
  var e = ETIQUETA_ESTADO[estado];
  return '<span class="chip ' + e[0] + '">' + e[1] + '</span>';
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

function pintarCampos() {
  var r = D.resumen;
  var campos = [
    {href: 'html/estadisticas.html', num: '1', titulo: 'Estadísticas generales',
     glosa: 'Las sesiones de 2024, 2025 y 2026 en las veinte localidades.'},
    {href: 'html/zoom.html', num: '2', titulo: 'Zoom año en curso',
     glosa: 'Cómo va cada localidad en 2026 y qué ajustes tiene su registro.'},
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

function pintarFranjaAnios() {
  var t = D.totales_serie;
  franja('franja-anios', [
    {v: t.a2024, rot: 'Actas 2024', glosa: 'Año completo, con sesiones ' +
     'mensuales.'},
    {v: t.a2025, rot: 'Actas 2025', glosa: 'Año completo, ya con sesiones ' +
     'ordinarias bimensuales.'},
    {v: t.a2026 + '*', rot: 'Actas 2026', glosa: 'Año en curso, con corte ' +
     'al ' + D.corte + '.'}
  ]);
}

function pintarSerie() {
  var filas = D.serie.map(function (l) {
    return '<tr><td>' + l.localidad + '</td>' +
      '<td>' + l.a2024 + '</td>' +
      '<td>' + l.a2025 + '</td>' +
      '<td>' + l.a2026 + '</td></tr>';
  }).join('');
  var t = D.totales_serie;
  document.getElementById('tabla-serie').innerHTML = filas +
    '<tr class="total"><td>Total</td>' +
    '<td>' + t.a2024 + '</td><td>' + t.a2025 + '</td>' +
    '<td>' + t.a2026 + '</td></tr>';
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

function pintarAccesosZoom() {
  var r = D.resumen;
  var fichas = [
    {href: 'periodicidad.html', cifra: r.al_dia_sesiones + ' de 20',
     nombre: 'Periodicidad de las sesiones',
     glosa: 'Localidades con las ' + r.ordinarias_exigidas +
            ' sesiones ordinarias que se esperan al corte, y consulta de ' +
            'sesiones por mes y localidad.'},
    {href: 'documentos.html',
     cifra: r.sesiones_completas + ' de ' + r.sesiones_formulario,
     nombre: 'Documentos de cada sesión',
     glosa: 'Sesiones con todos sus soportes cargados en el formulario.'},
    {href: 'pendientes.html', cifra: r.con_pendientes,
     nombre: 'Qué queda pendiente de cargar',
     glosa: 'Localidades con alguna sesión o documento por entregar.'},
    {href: 'detalle.html', cifra: r.actas_con_ajustes,
     nombre: 'Ajustes por acta',
     glosa: 'Actas que necesitan algún ajuste en su registro.'},
    {href: 'ajustes.html', cifra: r.localidades_con_ajustes,
     nombre: 'Ajustes por localidad',
     glosa: 'Localidades con alguna acta por ajustar.'}
  ];
  // Lo que se hizo y cómo se revisa van separados: Periodicidad queda bajo
  // el panorama general y el resto bajo el resumen de ajustes.
  var bloques = {'accesos-sesiones': ['periodicidad.html'],
                 'accesos-revision': ['documentos.html', 'pendientes.html',
                                      'detalle.html', 'ajustes.html']};
  Object.keys(bloques).forEach(function (id) {
    var nodo = document.getElementById(id);
    if (!nodo) return;
    nodo.innerHTML = fichas.filter(function (f) {
      return bloques[id].indexOf(f.href) >= 0;
    }).map(function (f) {
      return '<a class="acceso" href="' + f.href + '">' +
        '<div class="cifra">' + f.cifra + '</div>' +
        '<div class="nombre">' + f.nombre + '</div>' +
        '<div class="glosa">' + f.glosa + '</div>' +
        '<span class="entrar">Ver la página &rarr;</span></a>';
    }).join('');
  });
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

function pintarResumenAjustes() {
  var r = D.resumen;
  franja('franja-ajustes', [
    {v: r.limpias, rot: 'Actas ya listas',
     glosa: 'De ' + r.actas + '. No necesitan ningún ajuste.'},
    {v: r.num_problema, rot: 'Numeración por ajustar',
     glosa: 'El número que trae el acta por dentro no coincide con el del ' +
            'formulario o quedó vacío.'},
    {v: r.rec_problema, rot: 'Recuadros por completar',
     glosa: 'Al cuadro de participantes le falta algo o sus filas no suman.'},
    {v: r.cifras_difieren, rot: 'Cifras por conciliar',
     glosa: 'De ' + r.cifras_comparables + ' sesiones comparables.'}
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
  var M = D.meses;
  var nombres = M.nombres_consulta;
  var todas = D.localidades.map(function (l) { return l.localidad; });

  selLoc.innerHTML = '<option value="">Todas</option>' +
    todas.map(function (l) { return '<option>' + l + '</option>'; }).join('');
  var opciones = nombres.map(function (n, i) {
    return '<option value="' + (i + 1) + '">' + mayuscula(n) + '</option>';
  }).join('');
  selDesde.innerHTML = opciones;
  selHasta.innerHTML = opciones;
  selDesde.value = '1';
  selHasta.value = String(nombres.length);

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

    // Con una sola localidad elegida, la columna de localidad sobra
    var conLoc = !loc;
    var col = COLUMNAS.filter(function (c) { return c.id === orden.id; })[0];
    lista.sort(function (a, b) {
      var ka = col.clave(a), kb = col.clave(b);
      var d = ka < kb ? -1 : (ka > kb ? 1 : 0);
      if (!orden.asc) d = -d;
      // Los empates se desempatan por localidad y fecha, siempre en orden
      return d || (posicion(a) - posicion(b)) || (diaDelAnio(a) - diaDelAnio(b));
    });
    var cab = COLUMNAS.filter(function (c) {
      return conLoc || c.id !== 'localidad';
    }).map(function (c) {
      var activa = c.id === orden.id;
      var flecha = activa ? (orden.asc ? '&uarr;' : '&darr;') : '&varr;';
      return '<th' + (activa ? ' aria-sort="' +
          (orden.asc ? 'ascending' : 'descending') + '"' : '') + '>' +
        '<button type="button" class="ordenar' + (activa ? ' activa' : '') +
        '" data-col="' + c.id + '">' + c.rot +
        '<span class="flecha">' + flecha + '</span></button></th>';
    }).join('');
    var filas = lista.map(function (s) {
      return '<tr>' + (conLoc ? '<td>' + s.localidad + '</td>' : '') +
        '<td class="sin-corte">' + s.dia +
        '<span class="mes-largo"> de ' + nombres[s.mes - 1] + '</span>' +
        '<span class="mes-corto"> ' + nombres[s.mes - 1].slice(0, 3) +
        '</span></td>' +
        '<td class="sin-corte">' + s.tipo + '</td>' +
        '<td>' + miles(s.asistencias) + '</td>' +
        '<td>' + miles(s.jovenes) + '</td></tr>';
    }).join('');
    tabla.innerHTML = '<thead><tr>' + cab + '</tr></thead><tbody>' + filas +
      '<tr class="total"><td>Promedio</td>' + (conLoc ? '<td></td>' : '') +
      '<td></td><td>' + (n ? pA : '') + '</td>' +
      '<td>' + (n ? pJ : '') + '</td></tr>' +
      '</tbody>';
    tabla.parentNode.style.display = n ? '' : 'none';
  }

  // Orden de la tabla. Arranca por localidad, en el orden oficial de las 20,
  // y cambia con un clic en el título de una columna; el segundo clic lo
  // invierte. Las cifras arrancan de mayor a menor, que es lo que se busca
  // al ordenarlas. La fila de promedio queda siempre al final.
  function posicion(s) { return todas.indexOf(s.localidad); }
  function diaDelAnio(s) { return s.mes * 100 + s.dia; }
  var COLUMNAS = [
    {id: 'localidad', rot: 'Localidad', clave: posicion},
    {id: 'fecha', rot: 'Fecha', clave: diaDelAnio},
    {id: 'tipo', rot: 'Tipo', clave: function (s) { return s.tipo; }},
    {id: 'asistencias', rot: 'Asistentes', cifra: true,
     clave: function (s) { return s.asistencias; }},
    {id: 'jovenes', rot: 'Jóvenes', cifra: true,
     clave: function (s) { return s.jovenes; }}
  ];
  var orden = {id: 'localidad', asc: true};
  var tabla = document.getElementById('tabla-consulta');
  tabla.addEventListener('click', function (e) {
    var boton = e.target.closest('button.ordenar');
    if (!boton) return;
    var id = boton.getAttribute('data-col');
    if (orden.id === id) {
      orden.asc = !orden.asc;
    } else {
      orden.id = id;
      orden.asc = !COLUMNAS.filter(function (c) { return c.id === id; })[0].cifra;
    }
    actualizar(null);
    // La tabla se vuelve a pintar: el foco vuelve al mismo título para
    // quien ordena con el teclado
    var nuevo = tabla.querySelector('button[data-col="' + id + '"]');
    if (nuevo) nuevo.focus();
  });

  [selLoc, selDesde, selHasta].forEach(function (s) {
    s.addEventListener('change', function () { actualizar(s); });
  });
  actualizar(null);
}

function pintarDocumentos() {
  var filas = D.localidades.map(function (l) {
    return '<tr>' +
      '<td>' + l.localidad + '</td>' +
      '<td>' + l.sesiones_formulario + '</td>' +
      '<td>' + fraccion(l.actas, l.sesiones_formulario) + '</td>' +
      '<td>' + fraccion(l.planillas, l.sesiones_formulario) + '</td>' +
      '<td>' + (l.piden_digital
                ? fraccion(l.digitales, l.piden_digital)
                : '<span class="neutro">no aplica</span>') + '</td>' +
      '<td>' + chip(l.estado) + '</td></tr>';
  }).join('');
  var r = D.resumen;
  document.getElementById('tabla-documentos').innerHTML = filas +
    '<tr class="total"><td>Total</td>' +
    '<td>' + r.sesiones_formulario + '</td>' +
    '<td>' + r.actas + '</td>' +
    '<td>' + r.planillas + ' de ' + r.sesiones_formulario + '</td>' +
    '<td>' + r.digitales + ' de ' + r.piden_digital + '</td><td></td></tr>';
}

function pintarPendientes() {
  var bloques = D.localidades.filter(function (l) {
    return l.pendientes_sesion.length || l.pendientes_carga.length ||
           l.pendientes_imagen.length;
  }).map(function (l) {
    var todos = l.pendientes_sesion.concat(l.pendientes_carga)
                                   .concat(l.pendientes_imagen);
    return '<div class="bloque"><div class="nombre">' + l.localidad +
      '</div><ul>' + todos.map(function (p) {
        return '<li>' + p + '</li>';
      }).join('') + '</ul></div>';
  }).join('');
  document.getElementById('pendientes').innerHTML = bloques ||
    '<p>Ninguna localidad tiene sesiones ni documentos pendientes.</p>';
}

function pintarAjustes() {
  var filas = D.localidades.map(function (l) {
    var n = l.numeracion, c = l.recuadro;
    return '<tr>' +
      '<td>' + l.localidad + '</td>' +
      '<td>' + l.actas + '</td>' +
      '<td>' + pastilla(n.distinto + n.blanco + n.sin_linea) + '</td>' +
      '<td>' + pastilla(c.sin_recuadro + c.modificado + c.no_cuadra) + '</td>' +
      '<td>' + pastilla(l.cifras.difieren) + '</td>' +
      '<td>' + pastilla(l.fechas.difieren) + '</td>' +
      '<td>' + l.limpias + ' de ' + l.actas + barra(l.limpias, l.actas) +
      '</td></tr>';
  }).join('');
  var r = D.resumen;
  document.getElementById('tabla-ajustes').innerHTML = filas +
    '<tr class="total"><td>Total</td>' +
    '<td>' + r.actas + '</td>' +
    '<td>' + r.num_problema + '</td>' +
    '<td>' + r.rec_problema + '</td>' +
    '<td>' + r.cifras_difieren + '</td>' +
    '<td>' + r.fechas_difieren + '</td>' +
    '<td>' + r.limpias + ' de ' + r.actas + '</td></tr>';
}

function pintarDetalle() {
  document.getElementById('detalle').innerHTML =
    D.localidades.filter(function (l) { return l.detalle.length; })
    .map(function (l) {
      var items = l.detalle.map(function (d) {
        return '<div class="ajuste"><div class="archivo">' + d.archivo +
          '</div><ul>' + d.ajustes.map(function (h) {
            return '<li>' + h + '</li>';
          }).join('') + '</ul></div>';
      }).join('');
      return '<details class="localidad"><summary>' + l.localidad +
        '<span class="conteo">' + l.detalle.length +
        (l.detalle.length === 1 ? ' acta con ajustes' : ' actas con ajustes') +
        '</span></summary><div class="cuerpo">' + items + '</div></details>';
    }).join('');
}
