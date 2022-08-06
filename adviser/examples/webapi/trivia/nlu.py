import re
from datetime import datetime, timedelta
from typing import List

from utils.logger import DiasysLogger
from utils.domain.lookupdomain import LookupDomain
from utils import UserAct, UserActionType
from utils.sysact import SysAct
from utils.beliefstate import BeliefState
from services.service import Service, PublishSubscribe
from services.nlu import HandcraftedNLU


class TriviaNLU(HandcraftedNLU):
    """Adapted handcrafted NLU for the trivia domain. """

    def __init__(self, domain: LookupDomain, logger: DiasysLogger = DiasysLogger()):
        HandcraftedNLU.__init__(self, domain, logger)

    @PublishSubscribe(sub_topics=["user_utterance"], pub_topics=["user_acts"])
    def extract_user_acts(
        self,
        user_utterance: str = None,
        sys_act: SysAct = None,
        beliefstate: BeliefState = None
    ) -> dict(user_acts=List[UserAct]):
        result = {}
        self.user_acts = []
        self.slots_requested, self.slots_informed = set(), set()
        
        if not user_utterance:
            return {'user_acts': None}
        else:
            user_utterance = user_utterance.strip()
            # match the user utterance to a general act (like CONFIRM or DENY)
            # and add it to user_acts
            self._match_general_act(user_utterance)
            # match the user utterance to a domain spectific (like INFORM about
            # the answer to a question)
            self._match_domain_specific_act(user_utterance)

            # if the user utterance could not be matched to a general or domain
            # specific act, the user act Bad is selected and the user has to 
            # repeat the previous answer
            if len(self.user_acts) == 0:
                self.user_acts.append(
                    UserAct(
                        text=user_utterance if user_utterance else "",
                        act_type=UserActionType.Bad
                    )
                )
        self.logger.dialog_turn("User Actions: %s" % str(self.user_acts))
        return {'user_acts': self.user_acts}
