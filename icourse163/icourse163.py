import re
import json
import random

from icourse163.utils.util import camel_to_snake
from icourse163.utils.login import get_login_session
from icourse163.utils.util import raw_unicode_escape
from icourse163.utils.util import get_key_value

from icourse163.domain.term import Term
from icourse163.domain.test import Test
from icourse163.domain.post import Post
from icourse163.domain.reply import Reply
from icourse163.domain.comment import Comment
from icourse163.domain.answer import Answer
from icourse163.domain.course import Course
from icourse163.domain.member import Member
from icourse163.domain.question import Question
from icourse163.domain.term_score_summary import TermScoreSummary
from icourse163.domain.case_result import CaseResult
from icourse163.domain.answer_detail import AnswerDetail
from icourse163.domain.question_submit_record import QuestionSubmitRecord

from icourse163.dao.term_dao import TermDao
from icourse163.dao.test_dao import TestDao
from icourse163.dao.post_dao import PostDao
from icourse163.dao.reply_dao import ReplyDao
from icourse163.dao.comment_dao import CommentDao
from icourse163.dao.answer_dao import AnswerDao
from icourse163.dao.course_dao import CourseDao
from icourse163.dao.member_dao import MemberDao
from icourse163.dao.question_dao import QuestionDao
from icourse163.dao.summary_dao import SummaryDao
from icourse163.dao.case_result_dao import CaseResultDao
from icourse163.dao.answer_detail_dao import AnswerDetailDao
from icourse163.dao.question_submit_record_dao import QuestionSubmitRecordDao


session = get_login_session()
http_session_id = session.cookies["NTESSTUDYSI"]


def save_terms():
    # https://www.icourse163.org/collegeAdmin/teacherPanel.htm#/agt?type=1
    request_terms_url = "https://www.icourse163.org/dwr/call/plaincall/PublishCourseBean.getTermsByTeacher.dwr"
    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'PublishCourseBean',
        'c0-methodName': 'getTermsByTeacher',
        'c0-id': 0,
        'c0-param0': 1,
        'batchId': random.randint(1000000000000, 20000000000000)
    }

    response = session.post(url=request_terms_url, data=payload).text

    object_clear_regex = re.compile(r"s\d+\.")

    term = None
    course = None
    termDao = TermDao()
    courseDao = CourseDao()

    for line in response.splitlines():
        line = object_clear_regex.sub("", line)

        try:
            result = dict(map(lambda x: x.split('=', 1), line[:-1].split(';')))
        except ValueError:
            continue

        try:
            result["courseId"]
            result["fromTermId"]
            result["id"]
            result["schoolId"]
            term = Term(result)
            termDao.save(term)
        except KeyError:
            pass

        try:
            result["id"]
            result["schoolId"]
            result["videoId"]
            result["currentTermId"]
            print(result)
            result["name"] = raw_unicode_escape(result["name"])
            course = Course(result)
            courseDao.save(course)
        except KeyError:
            pass


def save_term_statistic(term_id):

    request_term_status_url = "https://www.icourse163.org/dwr/call/plaincall/MocScoreManagerBean.getMocTermDataStatisticDto.dwr"
    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'MocScoreManagerBean',
        'c0-methodName': 'getMocTermDataStatisticDto',
        'c0-id': 0,
        'c0-param0': term_id,
        'batchId': random.randint(1000000000000, 20000000000000)
    }

    response = session.post(url=request_term_status_url, data=payload).text

#    catch_pair_regex = re.compile(r's\d+\.([^\=]+)\=(([^"][^;]+)|(".*"));')
#    tuple((m.group(1), m.group(2)) for m in re.finditer(catch_pair_regex, line))

    test = None
    question = None
    testDao = TestDao()
    questionDao = QuestionDao()

    for line in response.splitlines():
        result = get_key_value(line)

        try:
            result["chapterId"]
            result["examId"]
            result["id"]
            result["termId"]
            result["description"] = raw_unicode_escape(result["description"])
            result["name"] = raw_unicode_escape(result["name"])
            test = Test(result)
            testDao.save(test)
        except KeyError:
            pass

        try:
            result["id"]
            result["testId"]
            result["optionsDetail"]
            result["description"] = raw_unicode_escape(result["description"])
            result["title"] = raw_unicode_escape(result["title"])
            result["plainTextTitle"] = raw_unicode_escape(result["plainTextTitle"])
            question = Question(result)
            questionDao.save(question)
        except KeyError:
            pass


def save_all_students_score(term_id):
    request_student_score_url = "http://www.icourse163.org/mm-tiku/web/j/mocTermScoreSummaryRpcBean.getStudentScorePagination.rpc?csrfKey={}".format(http_session_id)

    form_data = {
        "termId": term_id,
        "pIndex": 1,
        "pSize": 20,
        "rangeType": 1,
        "groupId": -1,
        "sort": 12,
        "searchName": "",
    }

    response = session.post(url=request_student_score_url, data=form_data).text
    response = json.loads(response)

    if response["result"]["query"] is not None:
        form_data["pSize"] = response["result"]["query"]["totleCount"]
        response = session.post(url=request_student_score_url, data=form_data).text
        response = json.loads(response)

        summary = None
        summaryDao = SummaryDao()

        for summary in response["result"]["list"]:
            term_score_summary = TermScoreSummary(summary)

            summaryDao.save(term_score_summary)
    else:
        print("Term {} doesn't have summary now".format(term_id))


def save_student_score_detail(member_id, term_id):
    request_student_score_detail_url = "http://www.icourse163.org/dwr/call/plaincall/MocScoreManagerBean.getSingleStudentScores.dwr"

    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'MocScoreManagerBean',
        'c0-methodName': 'getSingleStudentScores',
        'c0-id': 0,
        'c0-param0': member_id,
        'c0-param1': term_id,
        'batchId': random.randint(1000000000000, 20000000000000)
    }

    response = session.post(url=request_student_score_detail_url, data=payload).text

    catch_pair_regex = re.compile(r's\d+\.([^=]+)=([^;]+);')
    answer = None
    member = None
    answerDao = AnswerDao()
    memberDao = MemberDao()

    for line in response.splitlines():
        result = dict(re.findall(catch_pair_regex, line))

        try:
            if result["id"] == 'null':
                continue
            result["aid"]
            result["answererId"]
            result["examId"]
            result["testId"]
            result["tid"]
            result["name"] = raw_unicode_escape(result["name"])
            result["nickname"] = raw_unicode_escape(result["nickname"])
            answer = Answer(result)
            answerDao.save(answer)
        except KeyError:
            pass

        try:
            result["id"]
            result["email"]
            result["nickName"] = raw_unicode_escape(result["nickName"])
            result["realName"] = raw_unicode_escape(result["realName"])
            result["userName"] = raw_unicode_escape(result["userName"])
            result["description"] = raw_unicode_escape(result["description"])
            member = Member(result)
            memberDao.save(member)
        except KeyError:
            pass


def save_case_result(test_id, answer_id):
    request_term_status_url = "https://www.icourse163.org/dwr/call/plaincall/YocOJQuizBean.getOJPaperDto.dwr"

    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'YocOJQuizBean',
        'c0-methodName': 'getOJPaperDto',
        'c0-id': 0,
        'c0-param0': test_id,
        'c0-param1': answer_id,
        'batchId': random.randint(1000000000000, 20000000000000)
    }

    response = session.post(url=request_term_status_url, data=payload).text

    caseResult = None
    caseResultDao = CaseResultDao()

    for line in response.splitlines():
        result = get_key_value(line)

        try:
            result["caseId"]
            result["usedMemory"]
            result["passs"] = result["pass"]
            result["tips"] = raw_unicode_escape(result["tips"])
            result["testId"] = test_id
            result["answerId"] = answer_id
            print(result)
            caseResult = CaseResult(result)
            caseResultDao.save(caseResult)
        except KeyError:
            pass


def save_submit_record(test_id, answer_id):
    request_term_status_url = "https://www.icourse163.org/dwr/call/plaincall/YocOJQuizBean.adminGetOjQuestionSubmitRecords.dwr"

    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'YocOJQuizBean',
        'c0-methodName': 'adminGetOjQuestionSubmitRecords',
        'c0-id': 0,
        'c0-param0': test_id,
        'c0-param1': 'false',
        'c0-param2': answer_id,
        'batchId': random.randint(1000000000000, 20000000000000)
    }

    response = session.post(url=request_term_status_url, data=payload).text

    questionSubmitRecord = None
    questionSubmitRecordDao = QuestionSubmitRecordDao()

    for line in response.splitlines():
        result = get_key_value(line)

        try:
            result["questionId"]
            result["testAnswerformId"]
            result["testId"]
            result["userId"]
            print(result)
            questionSubmitRecord = QuestionSubmitRecord(result)
            questionSubmitRecordDao.save(questionSubmitRecord)
        except KeyError:
            pass


def save_answer_detail(test_id, answer_id):
    request_term_status_url = "https://www.icourse163.org/dwr/call/plaincall/MocQuizBean.getQuizPaperDto.dwr"

    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'MocQuizBean',
        'c0-methodName': 'getQuizPaperDto',
        'c0-id': 0,
        'c0-param0': test_id,
        'c0-param1': answer_id,
        'c0-param2': 'true',
        'batchId': random.randint(1000000000000, 20000000000000)
    }

    response = session.post(url=request_term_status_url, data=payload).text

    answerDetail = None
    answerDetailDao = AnswerDetailDao()

    for line in response.splitlines():
        result = get_key_value(line)

        try:
            result["qid"]
            result["score"]
            result["lastAnswerId"]
            result["score"]
            result["type"]
            result["testId"] = test_id
            result["answerId"] = answer_id
            print(result)
            answerDetail = AnswerDetail(result)
            answerDetailDao.save(answerDetail)
        except KeyError:
            pass


def save_user_post(user_id):
    def save_response(response):
        postDao = PostDao()

        for post in response["result"]["postsList"]:
            if post["lastReplyer"] == None or len(post["lastReplyer"]) <= 0:
                post["lastReplyerId"] = -1
            else:
                post["lastReplyerId"] = post["lastReplyer"]["id"]
                post["posterId"] = post["poster"]["id"]
                post_obj = Post(post)
                postDao.save(post_obj)

    request_user_post_url = "http://www.icourse163.org/web/j/MocPostRpcBean.getPostByUserId.rpc?csrfKey={}".format(http_session_id)

    form_data = {
        "p": 1,
        "psize": 20,
        "userId": user_id,
        "isOfficerPage": 0,
    }

    response = session.post(url=request_user_post_url, data=form_data).text
    response = json.loads(response)
    save_response(response)

    if response["result"]["pagination"] is not None:
        total_page = response["result"]["pagination"]["totlePageCount"]

        for page in range(2, (total_page+1)):
            form_data = {
                "p": page,
                "psize": 20,
                "userId": user_id,
                "isOfficerPage": 0,
            }

            response = session.post(url=request_user_post_url, data=form_data).text
            response = json.loads(response)

            save_response(response)

    else:
        print("User {} doesn't have post now".format(user_id))


def save_user_reply(user_id):
    def save_response(response):
        replyDao = ReplyDao()

        for reply in response["result"]["replyList"]:
            reply_obj = Reply(reply)
            replyDao.save(reply_obj)


    request_user_reply_url = "http://www.icourse163.org/web/j/MocPostRpcBean.getReplyByUserId.rpc?csrfKey={}".format(http_session_id)

    form_data = {
        "p": 1,
        "psize": 20,
        "userId": user_id,
        "isOfficerPage": 0,
    }

    response = session.post(url=request_user_reply_url, data=form_data).text
    response = json.loads(response)
    save_response(response)

    if response["result"]["pagination"] is not None:
        total_page = response["result"]["pagination"]["totlePageCount"]

        for page in range(2, (total_page+1)):
            form_data = {
                "p": page,
                "psize": 20,
                "userId": user_id,
                "isOfficerPage": 0,
            }

            response = session.post(url=request_user_reply_url, data=form_data).text
            response = json.loads(response)
            save_response(response)

    else:
        print("User {} doesn't have reply now".format(user_id))


def save_user_comment(user_id):
    def save_response(response):
        commentDao = CommentDao()

        for comment in response["result"]["commentList"]:
            comment_obj = Comment(comment)
            commentDao.save(comment_obj)

    request_user_comment_url = "http://www.icourse163.org/web/j/MocPostRpcBean.getCommentByUserId.rpc?csrfKey={}".format(http_session_id)

    form_data = {
        "p": 1,
        "psize": 20,
        "userId": user_id,
        "isOfficerPage": 0,
    }

    response = session.post(url=request_user_comment_url, data=form_data).text
    response = json.loads(response)
    save_response(response)

    if response["result"]["pagination"] is not None:
        total_page = response["result"]["pagination"]["totlePageCount"]

        for page in range(2, (total_page+1)):
            form_data = {
                "p": page,
                "psize": 20,
                "userId": user_id,
                "isOfficerPage": 0,
            }

            response = session.post(url=request_user_comment_url, data=form_data).text
            response = json.loads(response)
            save_response(response)

    else:
        print("User {} doesn't have comment now".format(user_id))


if __name__ == "__main__":
    session = get_login_session()
    http_session_id = session.cookies["NTESSTUDYSI"]

    # ???????????? - ????????????
    # http://www.icourse163.org/learn/JLU-62001?tid=1206772205&_trace_c_p_k2_=78e55f8bff9d4be3bda1161d877f18bc#/learn/quizscore?id=1220061754&aid=1481357597

    request_quiz_result_url = "http://www.icourse163.org/dwr/call/plaincall/MocQuizBean.getQuizPaperDto.dwr"

    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'MocQuizBean',
        'c0-methodName': 'getQuizPaperDto',
        'c0-id': 0,
        'c0-param0': id,
        'c0-param1': aid,
        'c0-param2': 'true',
        'batchId': random.randint(1000000000000, 20000000000000)
    }

    # ???????????? - ????????????
    # http://www.icourse163.org/learn/JLU-62001?tid=1206772205&_trace_c_p_k2_=40493107bde44512910441163f9bdac6#/learn/ojhw?id=1220061748&aid=1466334466&isCheck=1
    request_quiz_submit_records = "http://www.icourse163.org/dwr/call/plaincall/YocOJQuizBean.adminGetOjQuestionSubmitRecords.dwr"

    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'YocOJQuizBean',
        'c0-methodName': 'adminGetOjQuestionSubmitRecords',
        'c0-id': 0,
        'c0-param0': id,
        'c0-param1': 'false',
        'c0-param2': aid,
        'batchId': random.randint(1000000000000, 20000000000000)
    }

    # ???????????? - ???????????????????????????
    # http://www.icourse163.org/learn/JLU-62001?tid=1206772205&_trace_c_p_k2_=d66580f2348144909fb0175846cc712c#/learn/examObjectScore?id=1220061796&aid=1553103973&isCheck=1
    # ??? ???????????? - ????????????

    # ???????????? - ???????????????????????????
    # http://www.icourse163.org/learn/JLU-62001?tid=1206772205&_trace_c_p_k2_=b28950ebdc3f4d02b0d3bb90b5c2cf9e#/learn/examOj?id=1220061797&aid=1544038649&isCheck=1
    # ??? ???????????? - ????????????

    ask_video_url = "http://www.icourse163.org/dwr/call/plaincall/MocScoreManagerBean.getStudentScoresByExamId.dwr"

#    resp = session.post(url=ask_video_url, data=payload).text

    payload = {
        'callCount': 1,
        'scriptSessionId': '${scriptSessionId}' + str(random.randint(0, 200)),
        'httpSessionId': http_session_id,
        'c0-scriptName': 'CourseBean',
        'c0-methodName': 'getLastLearnedMocTermDto',
        'c0-id': 0,
        'c0-param0': 1206772205,
        'batchId': random.randint(1000000000000, 20000000000000)
     }
    cs_url = 'http://www.icourse163.org/dwr/call/plaincall/CourseBean.getLastLearnedMocTermDto.dwr'
#    rdata = session.post(cs_url, data=payload, timeout=None).text

