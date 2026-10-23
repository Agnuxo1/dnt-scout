# Auditoría independiente DNT-Scout — 23 de octubre de 2026

Objetivo: comprobar señal estructural y utilidad retrospectiva de la priorización de los 102 químicos del endpoint declarado. El criterio de éxito es evidencia reproducible de discriminación y ahorro de ensayos frente a azar; no se exige que este ensayo represente toda la neurotoxicidad.

Antes de ejecutar las pruebas nuevas se fijaron:

1. Reproducir el cálculo completo original en copia aislada, con las versiones Linux originales, y los 21 tests disponibles.
2. Reconstruir etiquetas desde el Excel EPA y fingerprints con RDKit; implementar read-across y selección anidada de forma independiente.
3. Repetir las 20 particiones publicadas y añadir 100 semillas 714001–714100. Repetir esas 100 con particiones que no usan etiquetas para asignar grupos.
4. Ejecutar 999 permutaciones de bloques de etiquetas entre scaffolds de igual tamaño, preservando correlación intragrupo y número de positivos, con todas las selecciones y asignaciones reejecutadas. Contraste unilateral y corrección (b+1)/(B+1). Hipótesis nula condicionada a tamaños de grupo; no es validación externa.
5. Comparar el ahorro con distribución exacta de orden aleatorio y medir sensibilidad a empates. Estos contrastes son retrospectivos sobre una cohorte enriquecida.
6. Examinar separadamente validez conformal y correspondencia entre modelo evaluado y exportado. No transferir una cobertura medida a otro modelo.

Se preservan los originales, no se publica ni se cambian cuentas. Cálculo con CPU, máximo cuatro hilos para el forest original y dos para álgebra; GPU no necesaria para el método actual. No se busca una semilla ganadora ni se promociona el mejor valor como rendimiento típico.
