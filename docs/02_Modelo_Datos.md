# Modelo de Datos

## Sistema de Gestión de Jineteadas

Este documento define las entidades principales del sistema y sus relaciones.

---

## 1. Usuarios

Tabla: `usuarios`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| nombre | string | Nombre visible |
| usuario | string | Usuario de acceso |
| password_hash | string | Contraseña encriptada |
| rol | string | ADMIN / SECRETARIA / LOCUCION |
| activo | boolean | Usuario habilitado |
| creado_en | datetime | Fecha de creación |

---

## 2. Campeonatos

Tabla: `campeonatos`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| nombre | string | Nombre del campeonato |
| anio | integer | Año |
| estado | string | BORRADOR / ACTIVO / CERRADO |
| creado_en | datetime | Fecha de creación |

---

## 3. Fechas

Tabla: `fechas`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| campeonato_id | integer | Relación con campeonato |
| numero | integer | Número de fecha |
| nombre | string | Nombre descriptivo |
| sede | string | Lugar |
| fecha_calendario | date | Día real |
| estado | string | PROGRAMADA / ABIERTA / CERRADA |

---

## 4. Categorías

Tabla: `categorias`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| nombre | string | Bastos / Gurupa / Clina |
| activa | boolean | Categoría habilitada |

---

## 5. Jinetes

Tabla: `jinetes`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| nombres | string | Nombres |
| apellidos | string | Apellidos |
| dni | string | DNI como texto |
| celular | string | Teléfono |
| email | string | Email opcional |
| creado_en | datetime | Fecha de alta |

---

## 6. Tropillas

Tabla: `tropillas`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| nombre | string | Nombre de la tropilla |

---

## 7. Caballos

Tabla: `caballos`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| nombre | string | Nombre del caballo |
| tropilla_id | integer | Relación con tropilla |
| pelaje | string | Pelaje |

El caballo se guarda una sola vez y se reutiliza en distintas fechas y categorías.

---

## 8. Preinscripciones

Tabla: `preinscripciones`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| uuid_qr | string | Código único para QR |
| campeonato_id | integer | Relación con campeonato |
| fecha_id | integer | Relación con fecha |
| categoria_id | integer | Relación con categoría |
| jinete_id | integer | Relación con jinete |
| estado | string | PREINSCRIPTO / CONFIRMADO / CANCELADO |
| creado_en | datetime | Fecha de preinscripción |
| confirmado_en | datetime | Fecha de confirmación |
| confirmado_por_id | integer | Usuario que confirmó |

El QR identifica una preinscripción específica, no al jinete.

---

## 9. Caballos disponibles

Tabla: `caballos_disponibles`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| campeonato_id | integer | Relación con campeonato |
| fecha_id | integer | Relación con fecha |
| categoria_id | integer | Relación con categoría |
| caballo_id | integer | Relación con caballo |
| estado | string | DISPONIBLE / SORTEADO / BAJA |

---

## 10. Sorteos

Tabla: `sorteos`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| campeonato_id | integer | Relación con campeonato |
| fecha_id | integer | Relación con fecha |
| categoria_id | integer | Relación con categoría |
| estado | string | BORRADOR / REALIZADO / ANULADO |
| creado_en | datetime | Fecha del sorteo |
| creado_por_id | integer | Usuario que lo realizó |
| observacion | text | Observaciones |

---

## 11. Montas

Tabla: `montas`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| sorteo_id | integer | Relación con sorteo |
| preinscripcion_id | integer | Relación con preinscripción |
| caballo_disponible_id | integer | Caballo sorteado |
| orden | integer | Orden de monta |
| palenque | integer | Palenque 1, 2 o 3 |
| puntos | float | Campo para carga posterior |
| observaciones | text | Observaciones |

---

## 12. Estado del jinete en campeonato

Tabla: `estado_jinete_campeonato`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| campeonato_id | integer | Relación con campeonato |
| jinete_id | integer | Relación con jinete |
| estado | string | ACTIVO / EN_REVISION / DESCALIFICADO / JUSTIFICADO |
| fechas_sin_puntos | integer | Fechas consecutivas sin puntos |
| observacion | text | Motivo o aclaración |
| actualizado_en | datetime | Última actualización |

Regla: si el jinete no suma puntos en dos fechas consecutivas queda EN_REVISION. Si al llegar la tercera fecha no se resolvió, queda DESCALIFICADO.

---

## 13. Bitácora

Tabla: `bitacora`

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | ID interno |
| campeonato_id | integer | Relación con campeonato |
| fecha_id | integer | Relación con fecha |
| categoria_id | integer | Relación opcional con categoría |
| usuario_id | integer | Usuario que realizó la acción |
| accion | string | Tipo de acción |
| descripcion | text | Descripción legible |
| entidad | string | Tabla o módulo afectado |
| entidad_id | integer | ID afectado |
| datos_extra | text/json | Información adicional |
| creado_en | datetime | Fecha y hora |

---

## Reglas principales

1. Un campeonato contiene varias fechas.
2. Una fecha pertenece a un campeonato.
3. Las categorías iniciales son Bastos, Gurupa y Clina.
4. Los jinetes se preinscriben por fecha y categoría.
5. El QR identifica una preinscripción específica.
6. Los caballos se cargan por fecha y categoría, pero se reutilizan si ya existen.
7. El sorteo aleatoriza jinetes y caballos.
8. Los palenques son siempre 1, 2 y 3 en rotación.
9. La tabla impresa debe incluir campo de puntos para jueces.
10. Toda acción importante queda registrada en bitácora.