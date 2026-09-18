# Jineteada 2026 — actualización para probar en develop

Base única: `C:\jineteada_26\jineteada_26.zip`. Este paquete conserva `app/` y `alembic/` en la raíz; se extrae **sobre el proyecto existente**, no dentro de `app/`. El ZIP recibido contenía esas carpetas, pero no `alembic.ini`, `requirements.txt`, `.env` ni la base de datos: se conservan los de tu instalación. No se modificó esa instalación ni se desplegó a producción.

## Cambios

- Clasificación por campeonato y categoría: F1+F2 >=5 activo, >0 y <5 repechaje, 0 descalificado. El repechaje es una instancia independiente ANTES de F3: >0 pasa a F3, 0 descalificado. Sus puntos NO se acumulan. Los resultados de F3 no resuelven el repechaje. Un campo sin puntaje no cuenta como cero y bloquea la finalización. Las fechas se ordenan por fecha/id del campeonato, excluyendo suspendidas, canceladas y reprogramadas; no se salta una F2 sin carga para usar F3 en su lugar. Las categorías que no puntúan no aplican esta regla.
- La clasificación se guarda en `jinete_campeonatos`, separada del estado y causa de sanción en `jinetes`. Inscripción, acreditación y sorteo comprueban ambos. Un repechaje aún sin confirmar bloquea el sorteo de F3 y posteriores de esa categoría. Se carga desde Resultados o Sorteos → Repechaje previo a F3, en pantalla o mediante Excel. Importar guarda un borrador: luego hay que confirmar todos los puntajes. Vacío es pendiente, no cero. Si cambia F1/F2, la planilla pierde vigencia y debe confirmarse de nuevo; no se puede reabrir con un sorteo posterior vigente. Reabrir resultados retira el cálculo que dependía de esa carga. Se conserva el alta manual posterior al cierre, antes del sorteo.
- Dos ausencias **consecutivas** siguen siendo una sanción independiente; se registra la causa. Se conserva la regla de suspensiones. No se levantan sanciones históricas automáticamente. La lógica deportiva vive en `app/services/clasificacion.py`, con una política pequeña preparada para parametrizar; no se introdujo un motor genérico.
- Resultados públicos muestran texto y distintivo: CLASIFICADO / REPECHAJE / DESCALIFICADO. Antes de resolver F1+F2 se muestra EN COMPETENCIA; las suspensiones/inactividades mantienen su nombre. La clasificación pública se calcula sólo con cargas publicadas.
- Campeonato: descripción, información, reglamento, publicación y enlace HTTPS opcional al documento. Se usa un enlace, sin agregar almacenamiento de archivos. Categorías: descripción y tipo de monta existentes como modalidad, más equipamiento. Los campeonatos de prueba permanecen fuera del portal. La migración conserva publicados los campeonatos oficiales activos/finalizados; los nuevos nacen sin publicar.
- Fechas pasadas: FINALIZADA en el portal, salvo excepciones. La corrección manual del estado público es independiente del estado operativo y no abre/cierra inscripciones. Una fecha pasada ya no alimenta el contador de próxima fecha.
- TV: pestañas Graph | Ticker | Tabla | Resultados. PVW y PGM independientes y persistentes para las cuatro salidas, incluyendo contenido, diseño y paginación. Seleccionar/preparar/editar modifica PVW; sólo **MANDAR AL AIRE** copia a PGM. **Limpiar PVW** conserva el aire. **Limpiar PGM** retira únicamente esa salida del aire y conserva PVW. Listado visible sólo en Graph; monitores ampliados de PVW arriba y PGM abajo. Las posiciones al aire quedan congeladas hasta otro envío. Se conservan tokens y rutas `/tv/salida/{token}/{graph|ticker|sorteo|campeonato}`. En la primera lectura tras migrar se copian los estados legacy a los nuevos buses, conservando lo que ya estaba al aire.

## Migración y prueba local

Detené la aplicación local antes de copiar y migrar. Guardá el ZIP como `C:\jineteada_26\jineteada_26_actualizacion_final.zip`. Verificá que estás en tu copia de desarrollo; no hagas push/deploy automático a producción. Cada comando siguiente ocupa una sola línea de PowerShell.

Comprobar rama y cambios locales:
```powershell
Set-Location C:\jineteada_26; git branch --show-current; git status --short
```

Respaldar código y SQLite con la aplicación detenida (si tu entorno usa PostgreSQL, respaldá esa base con tu procedimiento habitual antes de migrarla):
```powershell
Set-Location C:\jineteada_26; $respaldo=Join-Path '.\backups' ('antes_reformas_'+(Get-Date -Format 'yyyyMMdd_HHmmss')); New-Item -ItemType Directory -Path $respaldo | Out-Null; Copy-Item -LiteralPath '.\app','.\alembic','.\data' -Destination $respaldo -Recurse
```

Verificar revisión instalada antes de reemplazar (base esperada `a27c9d8e6104` si ya instalaste la actualización anterior, o `f6b1c92e4d70` si todavía no):
```powershell
Set-Location C:\jineteada_26; .\.venv\Scripts\python.exe -m alembic current
```

Reemplazar los archivos del paquete:
```powershell
Set-Location C:\jineteada_26; Expand-Archive -LiteralPath '.\jineteada_26_actualizacion_final.zip' -DestinationPath '.' -Force
```

Confirmar único head nuevo `b38da91f7205`, cuyo `down_revision` es `a27c9d8e6104`. Se conserva la migración anterior enlazada a `f6b1c92e4d70`:
```powershell
Set-Location C:\jineteada_26; .\.venv\Scripts\python.exe -m alembic heads
```

Migrar; si falla, no continúes con la recalculación:
```powershell
Set-Location C:\jineteada_26; .\.venv\Scripts\python.exe -m alembic upgrade head
```

Revisar la recalculación sin guardar nada:
```powershell
Set-Location C:\jineteada_26; .\.venv\Scripts\python.exe .\scripts\recalcular_clasificacion.py | Set-Content -LiteralPath '.\recalculo_previo.json' -Encoding utf8
```

Guardar clasificación, respetando todas las sanciones sin causa conocida:
```powershell
Set-Location C:\jineteada_26; .\.venv\Scripts\python.exe .\scripts\recalcular_clasificacion.py --aplicar | Set-Content -LiteralPath '.\recalculo_aplicado.json' -Encoding utf8
```

**Histórico:** la versión anterior no guardaba la causa; por eso no es posible distinguir automáticamente puntos de una sanción manual. `revision_manual` enumera los casos retenidos. Sólo tras verificar documentalmente el origen se pueden pasar IDs concretos al argumento `--confirmar-origen-puntos` (primero sin `--aplicar`). Aun así, el script exige 0<F1+F2<5 y bloquea casos con evidencia de ausencias o suspensión. No altera acreditaciones antiguas, sorteos ni puntajes. Guardá el informe de la operación.

Pruebas, con una base temporal propia (no usan tu base operativa):
```powershell
Set-Location C:\jineteada_26; .\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_reformas_2026.py -v
```

## Verificación realizada y límites

32 pruebas aprobadas: umbrales, F3, repechaje independiente antes de F3, bloqueo de sorteo, importación Excel, conservación del acumulado, separación por categoría, cargas incompletas/reapertura, sanciones, recalculación histórica, altas manuales, publicación/formularios HTTP y aislamiento de las cuatro salidas TV. Migración SQLite desde base vacía hasta head, downgrade del cambio nuevo y nuevo upgrade; SQL de las dos migraciones nuevas compilado para PostgreSQL. Plantillas y JavaScript generado verificados. No se ejecutó contra un servidor PostgreSQL real ni contra vMix: probar ambos en staging antes de producción.

Prueba operativa TV: preparar A y enviarlo; preparar B y verificar que PGM conserva A; recargar el panel; editar diseño y revisar sólo PVW; vaciar PVW y verificar que PGM sigue mostrando A; enviar vacío y comprobar transparencia. Repetir en cada pestaña y conservar las URLs actuales de vMix.


## Uso del repechaje

1. Finalizar F1 y F2 por categoría.
2. En Resultados o Sorteos abrir **Repechaje previo a F3**. No crear una fecha oficial para el repechaje, porque desplazaría la numeración de F3.
3. Cargar puntos directamente o exportar Excel, completar únicamente Puntos repechaje e importar. La planilla sólo admite los participantes con 0<F1+F2<5.
4. Revisar y pulsar **Confirmar repechaje**. Todo participante debe tener puntaje; ingresar 0 para quien no obtuvo puntos. Los sancionados siguen sin habilitación aunque sumen puntos.
5. Preparar/acreditar las inscripciones de F3 y sortear. Cada categoría se desbloquea por separado. Reabrir el repechaje vuelve a bloquearla.

La migración nueva no transforma los puntos de F3 en puntos de repechaje ni altera sorteos existentes. Si ya hubo sorteos de F3 bajo la interpretación anterior, revisarlos antes de continuar; la pantalla impide cambiar silenciosamente su clasificación. Sólo limpia estados calculados con causa `puntos_f3`; el comando de recalculación reconstruye la clasificación y conserva sanciones maestras.

## Antes de subir

Probar localmente y luego en staging PostgreSQL: migración, carga/confirmación del repechaje de una categoría de prueba, bloqueo/desbloqueo F3 y las cuatro salidas vMix. Respaldar la base de producción y revisar el diff antes de desplegar. No se ejecutó ningún despliegue y no debe enviarse develop directamente a producción.
