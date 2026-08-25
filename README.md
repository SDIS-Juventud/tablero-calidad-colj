# Tablero de seguimiento COLJ

Seguimiento a las sesiones y al registro documental de los Comités Operativos
Locales de Juventud de Bogotá, por localidad.

Publicado en https://sdis-juventud.github.io/tablero-calidad-colj/

## Cómo se regenera

Desde la raíz del proyecto:

```
python programas/generar_tablero_calidad_colj.py
```

El programa reescribe `index.html`, las páginas de `html/`, los datos de
`datos/` y los estilos de `recursos/`. Ninguno de esos archivos se edita a
mano.

Lo único que se edita a mano vive en `actualizacion/`. Las instrucciones
completas están en `actualizacion/COMO ACTUALIZAR.txt`.

## Metodología

La metodología, las fuentes y el alcance están en el documento «Nota
metodológica COLJ 2026», que no hace parte de este repositorio.
