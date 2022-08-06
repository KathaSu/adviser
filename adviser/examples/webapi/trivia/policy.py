from typing import List, Dict

from utils.domain.lookupdomain import LookupDomain
from services.service import PublishSubscribe, Service
from utils import SysAct, SysActionType
from utils.logger import DiasysLogger
from utils.useract import UserAct, UserActionType
from collections import defaultdict
from utils.beliefstate import BeliefState
from utils import SysAct


class TriviaPolicy(Service):
    """ 
    Define the policy for the trivia domain.

    The policy handles which system act should be next shown to the user. 
    """
    def __init__(self, domain: LookupDomain, logger: DiasysLogger = DiasysLogger()):
        # only call super class' constructor
        self.first_turn = True
        Service.__init__(self, domain=domain, debug_logger=logger)

    @PublishSubscribe(
        sub_topics=["beliefstate"],
        pub_topics=["sys_acts", "sys_state"]
    )
            
    def generate_sys_acts(
            self,
            beliefstate: BeliefState = None,
            sys_act: SysAct = None
        ) -> dict(sys_acts=List[SysAct]):
      
        # show the welcome of the trivia domain and ask the user if they 
        # want to customize the game
        if self.first_turn and not beliefstate['user_acts']:
            self.first_turn = False
            return {'sys_acts': [SysAct(SysActionType.Welcome)]}
        # ask the user to repeat the user utterance
        elif UserActionType.Bad in beliefstate["user_acts"]:
            return { 'sys_acts': [SysAct(SysActionType.Bad)] }
        # stop the trivia domain
        elif UserActionType.Bye in beliefstate["user_acts"]:
            return { 'sys_acts': [SysAct(SysActionType.Bye)] }
        # denies the user the wish to cutomize the game, these default 
        # informables are set    
        elif UserActionType.Deny in beliefstate["user_acts"]:
            self.domain.level = 'easy'
            self.domain.quiztype = 'boolean'
            self.domain.category = 'general'
            self.domain.length = 'infinity'
        # confirms the user the wish to customize the game, in the next 
        # steps the user is asked to fill in the informables (level, 
        # quiztype, category and length)
        else:
            # get the informables the were added in the previous step to the 
            # belief state from the user utterances
            constraints = beliefstate['informs']

            # if a informable is available store it in the domain class, 
            # where everything concerning the domain is stored
            if constraints:
                if 'level' in constraints:
                    self.domain.level = constraints['level']
                if 'quiztype' in constraints:
                    self.domain.quiztype = constraints['quiztype']
                if 'category' in constraints:
                    self.domain.category = constraints['category']
                if 'length' in constraints:
                    self.domain.length = constraints['length']
            
            # define the SysAct to ask for the level of the quiz
            if not self.domain.level:
                return {
                    'sys_acts': [
                        SysAct(SysActionType.Customize, slot_values={
                            'slot': 'level'
                        })
                    ]
                }
            # define the SysAct to ask for the quiztype of the quiz
            elif not self.domain.quiztype:
                return {
                    'sys_acts': [
                        SysAct(SysActionType.Customize, slot_values={
                            'slot': 'quiztype'
                        })
                    ]
                }
            # define the SysAct to ask for the category of the quiz
            elif not self.domain.category: 
                return {
                    'sys_acts': [
                        SysAct(SysActionType.Customize, slot_values={
                            'slot': 'category'
                        })
                    ]
                }
            # define the SysAct to ask for the length of the quiz
            elif not self.domain.length:
                return {
                    'sys_acts': [
                        SysAct(SysActionType.Customize, slot_values={
                            'slot': 'length'
                        })
                    ]
                }
        
        # if the requestable 'score' is present the user wants to know the 
        # current score 
        if beliefstate['requests'] == 'score':
            # define the relevant SysAct to tell the score to the user 
            # depanding on the quiztype. First the score is told, second the 
            # previous question is repeated.
            tell_score = SysAct(
                SysActionType.TellScore, slot_values={
                    'count': "None" if self.domain.count == 0 else str(self.domain.count),
                    'score': str(self.domain.score),
                    'length': 'infinity' if self.domain.length == 'infinity' else 'number',
                }
            )
            tell_previous_question = SysAct(
                SysActionType.TellPreviousQuestion, slot_values={
                    'quiztype': self.domain.quiztype,
                    'question': self.domain.question
                }
            )                
            if self.domain.quiztype == 'boolean':
                return {
                    'sys_acts': [tell_score, tell_previous_question]
                }
            else:
                possible_answers = self.domain.correct_answer | self.domain.incorrect_answers
                tell_answer_options = SysAct(
                    SysActionType.TellAnswerOptions, slot_values={
                        'a': possible_answers['a'],
                        'b': possible_answers['b'],
                        'c': possible_answers['c'],
                        'd': possible_answers['d']
                    }
                )
                return {
                    'sys_acts': [
                        tell_score,
                        tell_previous_question,
                        tell_answer_options
                    ]
                }

        # store the previous correct answer to compare them later
        prev_correct_answer = self.domain.correct_answer
        # get a new question from the domain
        self.domain.find_entities(beliefstate["informs"])

        # define the first question with answer options
        tell_first_question = SysAct(
            SysActionType.TellFirstQuestion, slot_values={
                'question': self.domain.question,
                'quiztype': self.domain.quiztype,
            }
        )
        if self.domain.quiztype == 'multiple':
            possible_answers = self.domain.correct_answer | self.domain.incorrect_answers
            tell_answer_options = SysAct(
                SysActionType.TellAnswerOptions, slot_values={
                    'a': possible_answers['a'],
                    'b': possible_answers['b'],
                    'c': possible_answers['c'],
                    'd': possible_answers['d']
                }
            )
        
        # if no answer (requestable) is available define the SysAct to tell 
        # the first question to the user
        if not beliefstate['requests']:
            self.domain.count += 1
            if self.domain.quiztype == 'boolean':
                return {
                    'sys_acts': [tell_first_question]
                }
            else:
                return {
                    'sys_acts': [tell_first_question, tell_answer_options]
                }
        
        # if a answer is avaibable (requestable) define the following variables:
        # - is the answer to the previous question correct
        if self.domain.quiztype == 'boolean':
            is_correct = True if beliefstate['requests'] == str(prev_correct_answer) else False
        else:
            is_correct = True if beliefstate['requests'] in prev_correct_answer else False
        # - convert the is_correct variable into text for the template
        correct_text = 'correct' if is_correct else 'incorrect'
        # - correct answer for a multiple choice question if the incorrect 
        #   answer was given
        correct_answer_text = [
            f'{key.capitalize()}) {value}' for key, value in prev_correct_answer.items()
        ][0] if not is_correct and self.domain.quiztype == 'multiple' else "None"

        # define the relavant SysAct for the second and later questions, 
        # depanding on quiztype and length
        tell_given_answer = SysAct(
            SysActionType.TellGivenAnswer, slot_values={
                'given_answer': correct_text,
            }
        )
        tell_correct_answer = SysAct(
            SysActionType.TellCorrectAnswer, slot_values={
                'correct_answer': correct_answer_text,
            }
        )
        tell_next_question = SysAct(
            SysActionType.TellNextQuestion, slot_values={
                'question': self.domain.question,
                'quiztype': self.domain.quiztype,
            }
        )
        tell_end = SysAct(
            SysActionType.TellEnd, slot_values={
                'quiztype': self.domain.quiztype,
                'length': 'infinity' if self.domain.length == 'infinity' else 'number',
                'score': str(self.domain.score),
                'count': str(self.domain.count),
            }
        )

        try:
            # if the length convertable into an integer, the length is not 
            # infinity and thus works different
            int(self.domain.length)
        except ValueError:
            # this defines the procedure for a infitiy game. The game end after 
            # the first wrong answer.
            self.domain.count += 1
            if is_correct:
                if self.domain.quiztype == "boolean":
                    return {
                        "sys_acts" : [tell_next_question]
                    }
                else:
                    return {
                        "sys_acts" : [tell_next_question, tell_answer_options]
                    }
            else:
                return {
                    "sys_acts": [tell_end]
                }
        else:
            # this defines the prodecure for an set number of questions game. 
            # The game ends after that number of questions.
            self.domain.count += 1
            # only continue if the length is lower than the count of the game
            if self.domain.count <= int(self.domain.length):
                self.domain.score += 1 if is_correct else 0
                if self.domain.quiztype == "boolean":
                    return {
                        "sys_acts" : [tell_given_answer, tell_next_question]
                    }
                else:
                    
                    return {
                        "sys_acts" : [
                            tell_given_answer,
                            tell_correct_answer,
                            tell_next_question,
                            tell_answer_options
                        ]
                    }
            else:
                if self.domain.quiztype == "boolean": 
                    return {
                        "sys_acts": [tell_given_answer, tell_end]
                    }
                else:
                    return {
                        "sys_acts": [
                            tell_given_answer,
                            tell_correct_answer,
                            tell_end
                        ]
                    }

        sys_state = {'last_act': sys_act}
        
        self.debug_logger.dialog_turn("System Action: " + str(sys_act))
        
        return {
            'sys_acts': [sys_act],
            'sys_state': sys_state,
        }
