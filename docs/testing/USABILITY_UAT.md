# Usability and user acceptance study

This is a collection template. No participant responses, satisfaction scores or acceptance decisions have been collected by the automated tests.

## Method

Recruit approximately ten consenting participants from the intended audience. Include different levels of familiarity with news apps; record recruitment and limitations rather than claiming a representative population. Use anonymous participant IDs, a disposable account, the same article snapshot and written tasks. Record device/browser/version and whether the participant has used the system before. Explain that the system is being evaluated, not the person. Do not collect account passwords or unnecessary personal information.

Give each task without demonstrating the solution first. Record independent completion, assisted completion or failure, time, errors and requests for help. Define a time limit in advance (for example three minutes per task); record timed-out tasks separately rather than excluding them from success rates. Test on the participant's normal device where possible.

## Task sheet

| Task | Instruction to participant | Observable completion condition |
|---|---|---|
| T1 | Find a specified news headline using search | Correct article located |
| T2 | Show Technology articles from a chosen publisher, then clear the filters | Correct filtered list and restored list |
| T3 | Open an article and explain its sentiment label in your own words | Article opened; interpretation recorded without prompting |
| T4 | Find its trust explanation and compare a linked related report | Participant identifies source/evidence and recognizes indicator limitations |
| T5 | Read the summary, then the supplied original excerpt | Participant reports whether the main information is preserved |
| T6 | Bookmark an article and find it again | Bookmark appears in the expected account's saved list |
| T7 | Refresh the selected publishers and identify completion/failure | Participant distinguishes pending state from result |
| T8 | Sign out, use a second test account and check saved articles | Participant can switch accounts; private activity stays isolated |

If an article has no related report, use a prepared example that does; do not invent a side-by-side comparison feature. If a source is unavailable, record the condition and assess the visible failure feedback.

## Observer record — copy once per participant

Participant ID: ____  Date: ____  Build: ____  Browser/version: ____  Device: ____

| Task | Independent / assisted / failed | Time (seconds) | Errors | Help requested | Observations |
|---|---|---|---|---|---|
| T1 | | | | | |
| T2 | | | | | |
| T3 | | | | | |
| T4 | | | | | |
| T5 | | | | | |
| T6 | | | | | |
| T7 | | | | | |
| T8 | | | | | |

## Questionnaire

Use **1 = strongly disagree, 2 = disagree, 3 = neither agree nor disagree, 4 = agree, 5 = strongly agree**. Provide `Not applicable / unable to judge` separately; do not encode it as 3.

| Item | Statement | Rating 1–5 or N/A |
|---|---|---|
| Q1 | I could find the news I wanted easily. | |
| Q2 | The category and publisher filters were clear. | |
| Q3 | The article page and navigation were easy to understand. | |
| Q4 | I understood what the sentiment result describes. | |
| Q5 | The trust explanation helped me decide what to verify. | |
| Q6 | I understood that the trust score does not prove an article is true. | |
| Q7 | The summary preserved the main information in the text I checked. | |
| Q8 | Loading, refreshing and error messages were clear. | |
| Q9 | Text and controls were usable on my device. | |
| Q10 | Overall, I was satisfied with the system. | |

Open questions: Which task was most difficult? What was confusing or missing? What one change would most improve the system? Did a summary or analysis label mislead you? Record specific examples.

## Analysis plan

Report participant count, task completion percentages with raw numerators/denominators, independent versus assisted completion, median task time and errors. Include timed-out/failed tasks in the completion denominator and describe how their times are reported. For each Likert item report valid response count, rating distribution and median; a mean may be supplementary. Do not present these custom items as a validated SUS score.

Group open comments into themes and retain contradictory feedback. A small convenience sample supports formative improvements, not broad statistical claims. Treat perceived summary accuracy separately from the independent source-comparison evaluation.

Example criteria to agree **before** the study: at least 8/10 independently complete core search/filter/detail tasks; median Q1/Q3/Q4/Q6 >=4 among valid responses; no unresolved critical privacy or misleading-score issue. These are proposed project criteria, not established results or universal standards.

## Compatibility and accessibility record

Run login, feed search/filter, detail/analysis, bookmark, account-switch and error-state tasks in each chosen browser. Record exact versions and actual devices; emulation is a separate method. Suggested viewports: 375×812, 768×1024 and 1440×900. Check keyboard navigation/focus, readable labels, zoom at 200%, text contrast, touch controls, reduced motion and dark/light mode. Record failed checks with screenshots and steps.

| Browser / OS / device / version | Actual device or emulation | Task results | Accessibility observations | Evidence / date |
|---|---|---|---|---|
| Chrome desktop | | Not run | | |
| Edge desktop | | Not run | | |
| Firefox desktop | | Not run | | |
| Chrome Android | | Not run | | |
| Safari iOS | | Not run | | |

## UAT decision

Reviewer ID/role: ____  Date/build: ____  Environment: ____

| Requirement | Evidence reviewed | Accepted / conditional / rejected | Condition or defect |
|---|---|---|---|
| Collection, filtering and article retrieval | | | |
| Sentiment and summary understandable | | | |
| Trust explanation and limitations clear | | | |
| Account and saved-article privacy | | | |
| Agreed response-time targets | | | |
| Core browser/device support | | | |

Overall decision: ____  Required changes: ____  Retest date: ____  Reviewer acknowledgement: ____

Do not mark acceptance on behalf of participants or the supervisor. Attach actual evidence and unresolved defects to the final Chapter 5 results.
