# ScipioTyping 1.7.0

Version 1.7.0 adds Guest to the learner chooser. The Guest PIN is hardcoded as
`8675309`, as requested, and works in both hosted and offline modes.

Guest exercises retain live typing feedback and final scoring, but the server
does not create a Guest database profile or save attempts, active time,
achievements, placement, or targeted-practice history. The interface labels
Guest mode and omits saved-progress and Parent navigation.

No database migration is required; schema 8 and all existing learner records
remain unchanged.
