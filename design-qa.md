# Design QA — Storybook Editorial

## Comparison target

- Source visual truth: Figma file `https://www.figma.com/design/ppdGzxWqTyJjksp93Ou0Oe`
- Student source frame screenshot: `/private/tmp/wfj-student-figma.png`
- Teacher source frame screenshot: `/private/tmp/wfj-teacher-figma.png`
- Student implementation screenshot: `/private/tmp/engwriting-student-desktop.png`
- Teacher implementation screenshot: `/private/tmp/engwriting-teacher-desktop.png`
- Accepted fusion reference: `/Users/allmind/.codex/generated_images/019f499f-d74e-7741-a3e9-2689392e13b5/exec-e3e35ada-5303-40c0-95f4-53e46005895c.png`
- Login mascot screenshot: `/private/tmp/engwriting-login-mascot.png`
- Student home mascot screenshot: `/private/tmp/engwriting-student-home-mascot.png`
- Student feedback mascot screenshot: `/private/tmp/engwriting-student-feedback-mascot.png`
- Teacher report screenshot: `/private/tmp/engwriting-team-link-final.png`
- Exported PDF screenshot: `/private/tmp/engwriting-class-report-final.pdf.png`
- Responsive evidence: `/private/tmp/engwriting-student-mobile.png`, `/private/tmp/engwriting-teacher-mobile.png`
- New responsive evidence: `/private/tmp/engwriting-login-mobile-final.png`, `/private/tmp/engwriting-reports-mobile-final.png`
- Read-aloud source screenshot: `/var/folders/jx/wzl7_g513tn_66m6vmskc0wc0000gn/T/codex-clipboard-f8989510-1d47-4685-a98a-bbbc03f97bea.png`
- Read-aloud implementation screenshot: `/private/tmp/engwriting-integrated-player-final.png`
- Focused read-aloud crop: `/private/tmp/engwriting-integrated-player-focused.jpg`
- Side-by-side player comparison: `/private/tmp/engwriting-player-comparison.png`
- Login scrollytelling source: `/var/folders/jx/wzl7_g513tn_66m6vmskc0wc0000gn/T/codex-clipboard-389005b4-0ca0-4d6e-be1a-71e49db45f64.png`
- Final login evidence: `/private/tmp/engwriting-login-final-hero.png`, `/private/tmp/engwriting-login-final-wonder.png`, `/private/tmp/engwriting-login-final-form.png`
- Desktop viewport: 1440 × 1024
- Mobile viewport: 390 × 844
- State: public login, authenticated student home/Practice/feedback, authenticated teacher Marking/Reports, and downloaded report PDF
- Runtime: production Next.js, FastAPI, PostgreSQL, Redis, auth, worker, and LanguageTool services managed by Docker Compose; Next.js proxies the backend through the same origin

## Full-view comparison evidence

The accepted fusion reference, student implementation, teacher implementation, live Reports screen, and exported PDF were opened together in one comparison pass. The product preserves the approved composition: warm ivory canvas, navy editorial headings, lavender coaching/AI states, coral teacher release action, restrained borders, a large writing/evidence surface, and a clear decision rail. The new surfaces extend the same visual grammar instead of introducing a separate dashboard theme.

The full-view comparison remains sufficient for the primary writing and teacher screens. A focused crop was added for the read-aloud control because its compact transport, time label, and progress track are too small to judge reliably in a full-page capture.

## Required fidelity surfaces

- Fonts and typography: Georgia provides the editorial serif hierarchy and Avenir/Helvetica provides compact UI text. Heading/body contrast, weights, line heights, labels, and control typography match the approved professional direction.
- Spacing and layout rhythm: desktop frames preserve the source proportions, 20–24 px section gaps, 14–18 px radii, open writing canvas, queue density, and fixed decision rail. Mobile layouts stack without hidden controls or horizontal page scrolling.
- Colors and tokens: warm ivory, deep navy, lavender, sage, pale blue, gold, and coral are mapped to shared CSS variables. Contrast remains readable in primary, disabled, warning, and evidence states.
- Image quality and assets: the AI Coach fox is a measured crop from the accepted visual source. It now appears consistently on login, student home, writing support, and released feedback, with role-appropriate scale and no stretching. The project-owned product mark remains in the header because no verified official school crest asset exists in the repository.
- Copy and content: visible static labels match the approved journey (`Draft`, `Polish`, `Share`, `My first draft`, `AI Coach`, `Live language support`, `Teacher Review Desk`, `Review queue`, `Release to student`). Task titles, writing, scores, comments, and counts intentionally come from live demo data.
- Icons: no placeholder emoji, ASCII art, CSS illustration, or handcrafted inline SVG was introduced. Existing product artwork and the source-derived coach asset are used instead.
- Interaction and states: student grammar check, live suggestion application, autosave state, teacher queue selection, evidence expansion, score editing, final-comment editing, and release confirmation remain functional.
- Read-aloud control: the former separate native playback row is replaced by one lavender capsule that expands in place to show Play/Pause, elapsed and total time, and seek progress. The native audio element remains hidden and accessible semantics expose the player and slider.
- Accessibility: semantic headings/regions, named buttons, labelled score/comment inputs, progressbar semantics, visible focus treatment, reduced-motion support, and mobile tap targets are present.

## Comparison history

### Iteration 1

- Finding: P2 responsiveness — the teacher screen expanded to 1044 px at a 390 px viewport because the review queue's min-content width propagated through the grid.
- Fix: added `minmax(0, 1fr)`, `min-width: 0`, explicit mobile max-width constraints, and a contained horizontal queue scroller.
- Post-fix evidence: browser metrics reported `viewportWidth: 390`, `documentWidth: 390`, `hasHorizontalOverflow: false`; `/private/tmp/engwriting-teacher-mobile.png` shows the corrected layout.

### Iteration 2

- Finding: P2 asset fidelity — the student AI Coach used the generic product mark instead of the warm coach character in the accepted direction.
- Fix: extracted the fox illustration from the accepted source at its measured card slot and added descriptive alt text.
- Post-fix evidence: the production student screenshot shows the fox in the lavender coach card without text overlap, stretching, or masking artifacts.

### Iteration 3

- Finding: P1 product coherence — the fox coach appeared only inside the writing editor, so login, student home, and returned feedback felt like unrelated generic screens.
- Fix: added one reusable mascot component and assigned the fox a specific job on each student-facing surface: welcome, next-step guidance, writing support, and reflection.
- Post-fix evidence: `/private/tmp/engwriting-login-mascot.png`, `/private/tmp/engwriting-student-home-mascot.png`, and `/private/tmp/engwriting-student-feedback-mascot.png` show consistent character, palette, typography, and restraint.

### Iteration 4

- Finding: P1 report usability — the former Reports view was a set of disconnected metric cards, generic operational states, and flat export history; the PDF was a plain line dump.
- Fix: rebuilt Reports around class completion, rubric averages, score distribution, teaching priorities, student evidence, and a clear export decision. Rebuilt PDF generation as a branded multi-page school report with summary metrics, rubric bars, teaching priorities, and a student table.
- Post-fix evidence: `/private/tmp/engwriting-team-link-final.png` and `/private/tmp/engwriting-class-report-final.pdf.png` show the same professional editorial system in-browser and in the downloaded artifact.

### Iteration 5

- Finding: P2 responsiveness — the new Reports screen expanded to 472 px at a 390 px viewport because grid min-content propagated through the workspace and native selects.
- Fix: set zero-min grid tracks plus explicit workspace, report-region, and topbar width constraints.
- Post-fix evidence: browser metrics reported `clientWidth: 390` and `scrollWidth: 390`; `/private/tmp/engwriting-reports-mobile-final.png` shows the corrected stacked report.

### Iteration 6

- Finding: P2 interaction hierarchy — read aloud created a second browser-native playback row below the trigger, making one action look like two unrelated controls.
- Fix: replaced the visible native audio bar with one in-place expanding capsule containing Play/Pause, elapsed/total time, and a seek slider. Kept the generated audio element hidden as the playback engine. Also moved the student header to a two-row layout below 980 px so Logout is never clipped.
- Post-fix evidence: `/private/tmp/engwriting-player-comparison.png` shows the two-row source state beside the single expanded control. Browser state reported one named audio player, one progress slider, no visible `audio[controls]`, `readyState: 4`, and `scrollWidth` equal to `innerWidth` at the 877 px in-app viewport.

### Iteration 7

- Finding: P1 visual identity — the public login still felt school-specific and component-led instead of matching the approved watercolor storybook reference.
- Fix: replaced the old school/product strip with the fox-led opening, botanical journey, alternating vocabulary chapters, real story illustrations, a gold reading trail, and a vine-framed sign-in destination. The app mark is now the transparent fox asset throughout the shell.
- Finding: P2 composition — the redundant hero brand strip, the right-side `wonder` text collision, and the excess gap before the sign-in card weakened the continuous story rhythm.
- Fix: removed the duplicate strip, moved `wonder` into the clean central opening, and brought the arrival section forward while preserving a calm transition.
- Finding: P2 interaction — reveal elements were unobserved after their first appearance, so the scrollytelling only played once.
- Fix: kept all reveal nodes observed and now toggles their state on both intersection entry and exit. Browser evidence confirmed `wonder` becomes visible again when scrolling upward while the arrival elements reset, then the arrival elements replay when scrolling downward.
- Post-fix evidence: `/private/tmp/engwriting-login-final-hero.png`, `/private/tmp/engwriting-login-final-wonder.png`, and `/private/tmp/engwriting-login-final-form.png`; the in-app browser reported zero horizontal overflow, all seven image assets loaded at natural size, no framework overlay, and no console errors.

## Final findings

- No actionable P0, P1, or P2 visual differences remain.
- P3 intentional deviation: the reference's exact botanical drawing is adapted into project-owned generated watercolor assets so the page remains school-neutral and production-safe.
- P3 intentional deviation: the teacher marking rail shows real per-student teaching follow-up instead of invented class-level percentages. Class-wide patterns remain the responsibility of the Reports screen and its report API.
- The former UAT-generated tasks, accounts, submissions, and audit noise were removed. The reset now creates a curated two-task P5A demo with one complete teacher-reviewed story, evidence comments, scores, follow-up exercise, and released feedback.

## Verification

- Page identity: passed for student Practice writing and teacher Marking.
- Non-blank meaningful content: passed.
- Framework overlay: passed in the final production preview.
- Student interaction: passed; `Check now` completed and refreshed the support state, and suggestion application was verified during the implementation loop.
- Teacher interaction: passed; the curated submission loaded its essay, linked evidence, editable scores, teacher comment, and teaching follow-up.
- Report interaction: passed; P5A auto-loaded at 50% completion with scores, teaching priorities, and two evidence rows.
- Export interaction: passed; PDF download completed, audit history updated, and the rendered two-page PDF passed visual inspection.
- Desktop visual evidence: passed at 1440 × 1024.
- Mobile visual evidence: passed at 390 × 844 with no horizontal overflow on login, teacher marking, and Reports.
- Temporary team URL: passed; public HTTPS login, teacher marking, and Reports completed through the same-origin backend proxy.
- MiniMax prompt read aloud: passed; the trigger expanded in place, the 8-second audio reached `readyState: 4`, and no second native control row was rendered.
- MiniMax writing read aloud: passed through the same component and returned a playable blob-backed audio asset.
- Submitted writing status: passed; seeded locked writing now renders `Submitted safely` instead of an erroneous autosave failure.
- Type check: passed.
- Frontend tests: 14 passed.
- Report/export tests: 3 passed, 2 database-gated tests skipped by their existing flag.
- Production build: passed.
- Full demo smoke: passed for web routes, API/Redis health, all three roles, real LLM prompt generation, LanguageTool grammar response, and Exam Mode suggestion blocking.

final result: passed
