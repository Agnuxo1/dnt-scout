# Guion del vídeo — DNT-Scout (3–5 min)

**Para Fran.** Las líneas en `> cita` son lo que dices, **en inglés** (las bases piden inglés o
chino). Todo lo demás son notas de producción en español. Duración objetivo **4:35**, dentro del
margen de 3–5 min. Son unas 600 palabras habladas: a ritmo tranquilo salen 4 minutos justos, así
que **no corras** — si te pasas de 4:30, corta el bloque 7 entero, está marcado como prescindible.

**Antes de grabar:**
- Ten abiertas en pestañas: (1) el GIF `results/figs/03_enrichment.gif` a pantalla completa,
  (2) el repo en GitHub, (3) el proyecto de SciencePal ya ejecutado.
- Graba la pantalla a 1920×1080. Si te grabas a ti, esquina inferior derecha, pequeño.
- Habla despacio y deja medio segundo de silencio entre bloques: facilita el montaje.

---

### 1 · El problema  `0:00 – 0:28`

**En pantalla:** negro con una sola frase, luego una placa MEA (foto libre o tu propia ilustración).

> Developmental neurotoxicity is one of the most expensive endpoints in toxicology, and one of the
> least covered. Tens of thousands of chemicals are in commerce. A few hundred have been tested.
>
> The *in vitro* alternative is to grow cortical neurons on a microelectrode array and watch whether
> they organise into a firing network. It is faster than an animal study — but it still costs days
> of culture, per compound.

*(Nota: no digas cifras que no estén en el documento. «Tens of thousands» y «a few hundred» son
seguras.)*

---

### 2 · La pregunta, hecha medible  `0:28 – 0:55`

**En pantalla:** la pregunta en texto grande, centrada.

> So the real constraint is not "is this chemical neurotoxic?". It is a scheduling problem: of the
> compounds nobody has tested, which ones go on the plate first?
>
> And that phrasing matters, because it makes the question measurable. The answer is not an accuracy
> number. It is: **how many assays do you have to run to find the actives?**

**Pausa de un segundo aquí.** Es la bisagra del vídeo.

---

### 3 · Qué cuenta como acierto  `0:55 – 1:35`

**En pantalla:** `results/figs/02_endpoint.png`, dejándola respirar. Señala con el cursor el panel
de la izquierda mientras hablas.

> First, the trap. A chemical that kills the culture flattens every electrophysiological parameter.
> Calling that "neuroactive" is the main way this kind of screen fools itself.
>
> So our outcome is defined *against* viability: a network effect counts only if it happens at least
> three-fold below the concentration that kills the cells. Forty-nine chemicals are selective,
> fifty-three show nothing in range — and twenty-eight are inconclusive, because their network
> effect only appears at lethal doses.
>
> Those twenty-eight are published and analysed. They are never quietly counted as negatives.

---

### 4 · El resultado  `1:35 – 2:15`

**En pantalla:** el GIF `03_enrichment.gif`, a pantalla completa. Déjalo correr entero.

> Here is the result. Testing in the order the model recommends, half the selective compounds are
> found after **thirty-two** assays. In a random order it takes **fifty-one and a half**. Across two
> hundred independent splits, thirty-three to thirty-four.
>
> That is about a third of the laboratory work removed. A perfect oracle would need twenty-five, so
> we capture roughly three quarters of the gain that is available at all.
>
> In accuracy terms: ROC area **0.828** on our pre-declared split, and **0.776** as the median over
> twenty others — I show you both, because they answer different questions.

---

### 5 · ¿Es real? La auditoría independiente  `2:15 – 3:25`

**En pantalla:** `results/figs/04_robustness.png`. Ve señalando panel a panel.

> We tried hard to break this. And then somebody else did.
>
> A separate agent, which did not share our code, reproduced the whole evaluation from a frozen
> commit. All one hundred and eighty-five numeric fields match. A re-implementation written from
> scratch agrees to five times ten to the minus seventeen. The labels, rebuilt independently from
> the EPA spreadsheet, are a hundred and thirty-six out of a hundred and thirty-six identical.
>
> And then the test that matters. **Nine hundred and ninety-nine label permutations**, swapping
> labels between scaffolds of equal size, and refitting the folds, the model selection and the
> predictions every single time. **Not one of them reached our result. p equals 0.001.**
>
> Our own attacks held too. Read-across votes on measured analogues — so does it just memorise
> close relatives? We hid every analogue above a similarity cap: at 0.7, the score is 0.820; at
> 0.5, 0.799. It is not memorisation. And on a harder split, holding out whole chemical clusters,
> performance drops to 0.74 — still far above chance, but the three model families converge. So
> read-across being the *best* model is specific to one split. Structure carrying real signal
> is not.

*(Nota: este bloque es el que más puntúa con un jurado de IA fiable. No lo recortes.)*

---

### 6 · Saber decir «no lo sé»  `3:25 – 3:50`

**En pantalla:** `results/figs/05_uncertainty.png`.

> A triage tool that answers every question is not calibrated — it is guessing.
>
> Every prediction carries a conformal set at ninety percent confidence. We promised ninety; the
> structural forest measured **89.2** on held-out scaffolds, and the read-across that actually
> ships measured **94.1** when the auditor checked it from the outside. The honest cost is that for
> sixty-three percent of chemicals the set contains both outcomes, and nearly eight percent fall
> outside the applicability domain altogether.
>
> Those are the queries where the correct output is a shrug. The tool gives one.

---

### 7 · SciencePal  `3:50 – 4:25`  *(prescindible si vas largo)*

**En pantalla:** EN DIRECTO, el proyecto de SciencePal. Enseña el agente corriendo y el informe que
devuelve. **Esto es criterio de evaluación: que se vea la plataforma funcionando, no una captura.**

> The central decision does not happen in my repository. It happens here, inside SciencePal.
>
> The Biology Agent gets the hundred and two measured analogues, and twenty chemicals withheld from
> every stage of fitting and calibration — and deliberately **not** our own answer, so it cannot
> copy it. It runs our scoring script in its own sandbox, resolves each structure, and writes a
> triage report.
>
> Two things happened that the ranking alone could not do. PubChem was **blocked** from that
> sandbox. The agent said so, instead of failing quietly, and went around it through CACTUS and the
> EPA registry — recovering **doxylamine**, a salt our pipeline had thrown away, and the only one
> of the twenty with a confident call. And it **overruled our ranking**, dropping oxytetracycline,
> because its nearest measured analogue is tetracycline at point five zero — the highest similarity
> anywhere in the set — and tetracycline shows no effect.
>
> I recomputed its three headline numbers myself before believing them. They reproduce exactly.

---

### 8 · Cierre  `4:25 – 4:35`

**En pantalla:** la URL del repo, grande, y debajo la del proyecto de SciencePal.

> This does not tell you a chemical is safe. A negative *in vitro* result does not exclude
> developmental neurotoxicity, and the OECD says so directly.
>
> What it tells you is which plate to run on Monday. Everything — data, code, every number in this
> video — is public and reproducible.

**Último plano:** congelar en la URL dos segundos. Sin música al final.

---

## Checklist antes de subir

- [ ] Duración entre 3:00 y 5:00
- [ ] Se ve SciencePal **en funcionamiento**, no una captura estática
- [ ] Se dicen en voz alta los dos ROC (0,828 predeclarado y 0,776 mediana) y el p = 0,001
- [ ] Se dice en voz alta que no es un veredicto de seguridad
- [ ] La URL del repo es legible a 720p
- [ ] Audio sin picos; normalizar a −16 LUFS si tu editor lo permite
