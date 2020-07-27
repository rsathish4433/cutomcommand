# customcommand_Teamcity
Trouble shoot the command


index=_internal  source="*customcommand_Teamcity.log"

Pass column id to thte custom command


search query:
| makeresults | eval KO_ID="1234" | teamcity id=KO_ID
