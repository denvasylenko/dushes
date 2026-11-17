# Tasks

Each numbered step from 2 on is one commit and one measurement by the QA Lead (D-23). A paid run starts only after
its price went to the CPO. Nothing in step 2 or later starts before step 1 is done.

## 0. Offline, free
- [x] 0.1 Read Anthropic's public guidance for agents (design.md lists the pages)
- [x] 0.2 The map: every rule of today's prompts -> the scenarios that cover it (design.md)
- [x] 0.3 The gaps and the draft fails-first set for the five points (design.md); the scenarios themselves are the QA Lead's
- [x] 0.4 The QA Lead confirms or corrects the map (it was made from each scenario's name, tags, goal and checks, not from held-out scenarios)

## 1. Before
- [x] 1.1 QA: the fails-first scenarios and the three new checks (questions before an action, words per reply, a claim without a tool result)
- [ ] 1.2 QA: the "before" pass on today's main (the default set, the held-out set, the cabinet's owner cases), Haiku, three repeats

## 2. Dushes' system prompt
- [ ] 2.1 Rewrite; every rule kept or covered; offline tests
- [ ] 2.2 QA: measurement; ships when no case is worse

## 3. The form agent's core prompt
- [ ] 3.1 Rewrite; every rule kept or covered; offline tests
- [ ] 3.2 QA: measurement

## 4. Tool descriptions and errors
- [ ] 4.1 Descriptions as for a new hire; each error says what to do and shows a correct call
- [ ] 4.2 QA: measurement (tool errors per run, repeated calls)

## 5. Tool merges
- [ ] 5.1 One look-up tool where several overlap; the old names keep working; the changelog names them
- [ ] 5.2 QA: measurement

## 6. The context of a turn
- [ ] 6.1 Trim the form context and the history to what the turn needs; the person's message last
- [ ] 6.2 QA: measurement (input tokens per turn, time to the first word)

## 7. Effort, measured only
- [ ] 7.1 QA: low against medium on the same set; the numbers go to the owner through the CPO

## 8. Release
- [ ] 8.1 QA: the final pass on the held-out set; "done" = no case worse than before, "understood the first time" better, the voice's first word within the D-20 threshold
- [ ] 8.2 A new package version with a changelog; docs pages after acceptance; the Cheese pin is Cheese's own (D-21)
