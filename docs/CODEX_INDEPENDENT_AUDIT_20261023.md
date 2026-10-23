# DNT-Scout: resultado reproducido y utilidad retrospectiva confirmada

Auditoría independiente de Codex, 23 de octubre de 2026. Proyecto: `E:/Proyecto-concursos/sciencepal-neurotox`. Referencia inicial: commit `38b00be`, con reproducción aislada del código Linux original. Se conservaron los originales; Claude estaba modificando documentación y etiquetas durante esta revisión. Los resultados del endpoint original se calcularon sobre el parquet congelado de 136 registros, 102 modelables con etiqueta binaria.

**Conclusión:** el trabajo contiene una señal estructural reproducible y una mejora útil de priorización dentro de la cohorte estudiada. El **0,828 es real bajo el protocolo publicado**. Las pruebas nuevas sostienen el ahorro de ensayos; las correcciones pendientes se concentran en cómo se describe y construye la incertidumbre del producto. La evidencia justifica continuar esta línea y pasar a una validación prospectiva con protocolo congelado.

## Qué significan 0,828, 0,776 y 0,696

| Evaluación | ROC AUC | Ensayos para recuperar aproximadamente la mitad de positivos | Comparador aleatorio |
|---|---:|---:|---:|
| Endpoint original, partición original: 102 químicos, 49 positivos | **0,827686** | **32 para encontrar 25** | **51,5 de media exacta** |
| Mismas 20 particiones de Claude, reproducidas | Mediana **0,776184** | Mediana **32,5**; mínimo–máximo 31–37 | 51,5 |
| 100 particiones nuevas con el protocolo original | Mediana **0,760204** | Mediana **33**; mínimo–máximo 29–44 | 51,5 |
| 100 particiones nuevas, grupos asignados sin etiquetas | Mediana **0,743935** | Mediana **34**; mínimo–máximo 30–42 | 51,5 |
| Sensibilidad: retirar 9 positivos no acotados suponiendo dosis máxima 20 µM; 93 químicos, 40 positivos | **0,832783** en semilla original; mediana **0,839269** en 20 particiones | **25 para encontrar 20**; mediana 25, rango 23–29 | **45,854** |
| Otro objetivo: selectivos frente a todos los demás, incluidos citotóxicos; 130 químicos | **0,696397** en semilla original; mediana **0,675611** en 20 particiones | **44 para encontrar 25**; mediana 43,5 | **65,5** |

Los valores responden a preguntas diferentes. La mediana de otras particiones no sustituye al resultado original; el endpoint con citotóxicos tampoco es la misma tarea. El 0,828 está visible en la tabla principal del README revisado: no encuentro evidencia de ocultación en esa versión. La presentación adecuada muestra resultado original, estabilidad y utilidad práctica juntos. ROC AUC no es porcentaje de aciertos ni cobertura conformal.

La sensibilidad de 93 químicos es favorable, pero cambia la población evaluada. Se calculó bajo el supuesto explícito de 20 µM como dosis máxima para los casos sin EC50 de citotoxicidad ajustada; esta auditoría no ha certificado la dosis máxima específica de cada uno. No se presenta como mejora demostrada del modelo sobre el mismo conjunto de 102 ni como validación externa.

![Auditoría cuantitativa](../work/codex-audit-20261023/DNT-Scout_auditoria.png)

## Evidencia nueva ejecutada

1. **Reproducción completa en servidor-ia:** copia aislada, entorno original NumPy 2.5.4 / scikit-learn 1.9.1 / RDKit 2026.09.1. Se reproducen los cuatro modelos, las predicciones, ROC AUC, PR AUC y cobertura del forest. Comparación automática de los campos numéricos y de las predicciones en `verification.json`.
2. **Implementación independiente:** nuevos fingerprints con RDKit, implementación propia del read-across, agrupamiento y selección anidada; no importa el motor CV ni los modelos originales. Diferencia máxima en predicciones de read-across: **5,55×10⁻¹⁷**. Las 20 AUC publicadas coinciden exactamente. ROC media calculada dentro de cada fold: **0,822098**; AUC agrupando puntuaciones originales sin normalizar: **0,802849**. Las tres variantes sostienen señal.
3. **999 permutaciones con reajuste completo:** se intercambian vectores de etiquetas entre scaffolds de igual tamaño, preservando correlación intragrupo, número de positivos y tamaños; se recalculan folds exteriores, selección interior y predicciones. Ninguna alcanza el AUC observado. Contraste unilateral **p = 0,001**, usando `(b+1)/(999+1)`; para presupuesto de ensayos, **p = 0,003**. La nula está condicionada a tamaños de scaffold y a esa intercambiabilidad; no representa cualquier posible sesgo biológico. Si se corrige de forma conservadora por las cuatro familias originales mediante Bonferroni, el p de AUC sería **0,004**. Estas repeticiones reutilizan la misma cohorte; no son 999 estudios biológicos independientes.
4. **200 particiones nuevas:** 100 con la regla original y 100 con agrupamiento que no mira etiquetas; semillas fijadas en `PROTOCOL.md` y scripts antes de ejecutar. Los rangos centrales de sensibilidad del AUC son 0,697–0,828 y 0,680–0,797. Son percentiles entre particiones sobre los mismos químicos, no intervalos de confianza independientes de rendimiento externo.
5. **Orden aleatorio exacto:** distribución del lugar que ocupa el positivo 25, sin aproximación Monte Carlo. Media **51,5**, intervalo central exacto del 95% **41–62**. Frente a 32, ahorro retrospectivo **37,9%**. La probabilidad combinatoria de encontrar al menos 25 positivos en 32 posiciones aleatorias es **3,68×10⁻⁵**; describe el orden aleatorio, no sustituye al contraste con todo el aprendizaje reajustado.
6. **Empates:** 10.000 desempates aleatorios mantienen el presupuesto en **32**. El resultado no depende del orden de almacenamiento de las filas empatadas.
7. **Datos:** reconstrucción independiente de las etiquetas desde el Excel EPA: **136/136 coinciden**. Coinciden los SHA256 de los tres archivos de entrada declarados. No hay duplicados de SMILES ni InChIKey entre los 102 modelados. Hay **73 grupos singleton de 81**: 90,1% de grupos, equivalentes a 71,6% de los químicos. El texto «72% de grupos» confunde esos denominadores.
8. **Tests originales:** 21/21 en la referencia inicial. El primer arranque de pytest tropezó con un plugin global ajeno al proyecto; se aisló con `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. El estado concurrente añade dos tests: **23/23 pasan**; las aserciones del candidato también se ejecutaron.

El protocolo de auditoría y las semillas se conservaron antes de ejecutar sus experimentos; no se afirma registro externo ni preregistro anterior al desarrollo de Claude. Una primera ejecución de la implementación independiente se descartó al detectar un denominador sumado en float32. Se corrigió para igualar la semántica float64 de `numpy.average`; el script definitivo exige concordancia <10⁻¹² antes de iniciar pruebas nuevas. Solo la ejecución final sustenta los resultados de este informe.

## Incertidumbre: nuevos resultados positivos y correcciones concretas

La cobertura del **89,2%** del repositorio corresponde a conjuntos conformales del **forest**, no al read-across que usa el paquete portátil. Para resolver esa diferencia, se evaluó el procedimiento portátil de forma exterior: LOO y cuantiles se calculan solo con cada entrenamiento exterior; los químicos de test no entran en ajuste ni calibración.

| Procedimiento | Cobertura en partición original | Mediana de cobertura en 20 particiones nuevas | Conjuntos con ambas clases, partición original |
|---|---:|---:|---:|
| Forest publicado | **89,2%** | No reestimada en esta tabla | 62,7% |
| **Read-across portátil original, validado ahora** | **94,1%** | **95,1%** | 63,7% |
| Candidato con ajuste/calibración separados antes de seleccionar hiperparámetros | **99,0%** | **95,6%** | 95,1% |

La nueva medición favorece al exportador: empíricamente cubre bien en estas particiones. Cobertura significa que la etiqueta observada está en el conjunto devuelto; un conjunto con ambas clases siempre cubre y no decide. Por eso no se vende el 99% del candidato como «más precisión»: es más conservador y menos informativo. En las 20 particiones nuevas, los conjuntos con ambas clases tienen mediana 75,0% en el original y 86,3% en el candidato. No hay justificación para reemplazar automáticamente el original por esa variante.

Correcciones proporcionadas al uso real del sistema:

- **Identificar el modelo de cada cifra.** Publicar la nueva cobertura del exportador junto a la del forest. El procedimiento LOO del exportador no demuestra por sí solo una garantía split-conformal exacta.
- **Separar ajuste y calibración antes de seleccionar hiperparámetros.** El forest actual elige hiperparámetros usando todo el entrenamiento exterior y después separa calibración. La cobertura observada conserva valor, pero no basta para la garantía teórica declarada.
- **Usar la misma referencia para el dominio.** El umbral del forest se calcula como similitud calibración→ajuste y se aplica con test→entrenamiento completo. La segunda opinión ejecutada obtiene 94/102 dentro del dominio con la referencia actual y 88/102 con la referencia de ajuste coherente. Cambia abstención, sin refutar el ranking.
- **Cuantiles con muestras pequeñas.** Si el orden estadístico necesario excede el número de calibración, usar el umbral conservador. Con puntuaciones de no conformidad acotadas en [0,1], un umbral 1 incluye ambas clases. El caso extremo de un ejemplo por clase reproduce un fallo reutilizable del componente original; no se activa en los cinco folds publicados del forest, cuyos mínimos por clase son nueve.
- **Una política química compartida para sales y mezclas.** El núcleo acepta el fragmento orgánico mayor de `CCO.CCCCC`, mientras que el exportador lo rechaza por multicomponente. El benzoato sódico también se acepta en el núcleo y se rechaza en el exportador. Hay que distinguir explícitamente sales de mezclas y aplicar la misma política al entrenamiento y al producto. Estos ejemplos no demuestran contaminación del conjunto evaluado.

Se entrega **`calibrated_readacross.py` como candidato independiente**, con pruebas ejecutadas de separación por scaffold, cuantiles en m=0/1/9 y la invariante de que cambiar etiquetas de calibración no altera hiperparámetros ni puntuaciones del modelo de ajuste. No se ha integrado sobre los archivos que Claude está editando.

## Herramientas y alcance científico

Se utilizaron RDKit, NumPy, SciPy, pandas, scikit-learn y pytest; son herramientas científicas existentes y adecuadas a esta tarea. La reproducción pesada del forest se ejecutó en CPU del servidor-ia en carpeta aislada. Las dos RTX 3090 estaban disponibles; estos métodos tabulares pequeños no necesitaban GPU. No se entrenó una red mayor para inflar el resultado ni se creó un laboratorio artificial.

Se consultó el [laboratorio virtual P2PCLAW](https://www.p2pclaw.com/lab/), aplicando la [skill lab-usage](C:/Users/Windows-500GB/.codex/plugins/cache/claude-cowork/anthropic-skills/1.0.0/skills/lab-usage/SKILL.md). Sus endpoints de estado y salud devolvieron **HTTP 403**, registrado en `virtual_lab_access.json`; no se atribuyen experimentos ni validaciones a ese servicio. La ejecución científica se completó con las herramientas disponibles. La documentación oficial de [GenRA, EPA](https://www.epa.gov/comptox-tools/generalized-read-across-genra-manual) confirma la familia de métodos y el uso de permutaciones para evaluar read-across; esta auditoría no afirma haber ejecutado el servicio GenRA.

El [estudio de Shafer et al.](https://pubmed.ncbi.nlm.nih.gov/30816951/) describe 136 químicos y este ensayo de formación de red. Los resultados aquí prueban concordancia predictiva y ahorro retrospectivo dentro de esa cohorte. No miden toxicidad clínica, ahorro económico real en laboratorio ni rendimiento prospectivo sobre una biblioteca de prevalencia desconocida. Tampoco corresponde exigir que un priorizador de este ensayo resuelva procesos biológicos que este ensayo no observa.

La normalización de puntuaciones por rangos dentro del fold es una definición de evaluación que debe declararse. No es la única «corrección» posible: la [documentación de scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.cross_val_predict.html) explica que métricas de predicciones agrupadas y medias entre folds pueden diferir. Que la prevalencia agrupada dé 0,473 no demuestra por sí solo que todo el pipeline fuera inválido. Aquí la media por fold 0,822 y el agrupado original 0,803 respaldan el resultado sin depender exclusivamente del 0,828 normalizado. Para una garantía conformal se necesitan las condiciones del procedimiento, incluidas las de intercambio: [Angelopoulos y Bates](https://arxiv.org/abs/2107.07511).

## Próximo experimento y presentación recomendada

**Texto de resultado recomendado:** «DNT-Scout reproduce ROC AUC 0,828 y recupera 25 de 49 positivos en 32 ensayos retrospectivos, frente a 51,5 al azar. La señal se mantiene al variar particiones; 200 particiones adicionales requieren típicamente 33–34 ensayos. Una evaluación más estricta de selectividad también es favorable, bajo el supuesto de dosis indicado. El read-across portátil obtiene cobertura exterior 94,1% en la partición original. Queda pendiente validación prospectiva sobre químicos nuevos con endpoint y dosis máximas definidos de antemano».

El siguiente experimento útil es congelar endpoint, modelo, política química, dominio, presupuesto y métricas; seleccionar una cohorte nueva sin consultar sus resultados; puntuar una sola vez y comparar el rendimiento por presupuesto con selección aleatoria y baselines. No usar el conjunto de 460 como validación externa independiente sin auditar solapamientos, porque contiene los 136 originales. Los 20 candidatos nuevos pueden servir para un piloto si se consiguen etiquetas de selectividad comparables; resultados sin viabilidad no contestan exactamente este endpoint.

El trabajo revisado merece una presentación positiva y precisa: el objetivo principal se sostiene, y las limitaciones señalan qué experimento hará la evidencia más fuerte. No hay base en esta auditoría para atribuir errores a «guardrails» del modelo ni para certificar una causa interna del comportamiento de Claude.

## Evidencia y reproducción

Paquete `DNT-Scout_evidencia_20261023.zip`: protocolo, scripts independientes y candidato, resultados completos JSON/CSV, logs finales, datos procesados de entrada, referencia de código congelada y manifiesto SHA256. No contiene credenciales ni los 159 MB de datos crudos.

Con las dependencias científicas del proyecto y los datos crudos originales disponibles, extraer el paquete y ejecutar en su carpeta:

```powershell
python independent_audit.py --root E:/Proyecto-concursos/sciencepal-neurotox --out .
python validate_calibration.py --root E:/Proyecto-concursos/sciencepal-neurotox --out .
python endpoint_sensitivity.py --out .
```

La primera orden verifica hashes de los datos crudos y compara contra la evaluación de referencia del proyecto. Si se actualiza esa referencia, usar la copia congelada incluida en `baseline-src` y proporcionar sus mismos datos crudos. Las aserciones detienen la auditoría si cambia la concordancia numérica. El candidato no requiere publicación ni acceso a cuentas.

JEV: decisiones remotas verificadas (`remote_decision=true`) para exploración, diseño, verificación y escritura; ejecución determinista, trabajo directo y una segunda opinión acotada de revisión metodológica. El cierre devolvió `provenance=jev`, `status=connected`, `ready_audit`, confianza 0,14: es una recomendación de baja confianza, no una validación científica adicional. La conclusión se sostiene en las ejecuciones y comprobaciones documentadas.
