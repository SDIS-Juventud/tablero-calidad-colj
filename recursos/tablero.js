
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
    'en que sesionó el último COLJ registrado, no el día de consulta.';
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

function pintarEnlaces() {
  var nodo = document.getElementById('enlaces');
  if (!nodo) return;
  nodo.innerHTML = D.enlaces.map(function (e) {
    var cuerpo = '<div class="nombre-enlace">' + e.nombre + '</div>' +
      '<div class="glosa">' + e.glosa + '</div>';
    if (e.url) {
      return '<a class="enlace" href="' + e.url + '" target="_blank" ' +
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
            ' sesiones ordinarias que se esperan al corte.'},
    {href: 'documentos.html',
     cifra: r.sesiones_completas + ' de ' + r.actas,
     nombre: 'Documentos de cada sesión',
     glosa: 'Sesiones con todos sus soportes cargados en el formulario.'},
    {href: 'pendientes.html', cifra: r.con_pendientes,
     nombre: 'Qué queda pendiente de cargar',
     glosa: 'Localidades con alguna sesión o documento por entregar.'},
    {href: 'detalle.html', cifra: r.localidades_con_ajustes,
     nombre: 'Ajustes por acta',
     glosa: 'Localidades con el detalle de qué corregir en cada acta.'},
    {href: 'ajustes.html', cifra: r.actas_con_ajustes,
     nombre: 'Ajustes por localidad',
     glosa: 'Actas que necesitan algún ajuste en su registro.'}
  ];
  var nodo = document.getElementById('accesos');
  if (!nodo) return;
  nodo.innerHTML = fichas.map(function (f) {
    return '<a class="acceso" href="' + f.href + '">' +
      '<div class="cifra">' + f.cifra + '</div>' +
      '<div class="nombre">' + f.nombre + '</div>' +
      '<div class="glosa">' + f.glosa + '</div>' +
      '<span class="entrar">Ver la página &rarr;</span></a>';
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

function pintarResumenAjustes() {
  var r = D.resumen;
  franja('franja-ajustes', [
    {v: r.limpias, rot: 'Actas ya listas',
     glosa: 'De ' + r.actas + '. No necesitan ningún ajuste.'},
    {v: r.num_problema, rot: 'Numeración por ajustar',
     glosa: 'El número que trae el acta por dentro no coincide con el del ' +
            'archivo o quedó vacío.'},
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
      ? 'Hoy, ' + r.en_silencio + (r.en_silencio === 1 ? ' localidad.' : ' localidades.')
      : 'Hoy, ninguna.';
  }
}

function pintarDocumentos() {
  var filas = D.localidades.map(function (l) {
    return '<tr>' +
      '<td>' + l.localidad + '</td>' +
      '<td>' + l.sesiones_formulario + '</td>' +
      '<td>' + fraccion(l.actas, l.sesiones_formulario) + '</td>' +
      '<td>' + fraccion(l.planillas, l.actas) + '</td>' +
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
    '<td>' + r.planillas + '</td>' +
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
