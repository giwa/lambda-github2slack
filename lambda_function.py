import threading
import urllib
import json
import os

from github import Github

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

with open(os.path.join(__location__, "conf.json")) as f:
    conf = json.load(f)

web_hook_url = conf['web_hook_url']
token = conf['github_token']
repos = conf['repositories']
channel = conf['channel']
username = conf['username']
orgname = conf['orgname']

git2slack= conf['github2slack']

slack_comment="""\
:alarm_clock: *Review Time*

{prs}


:sparkles:*Happy Coding!*:sparkles:
"""

pr_comment="""\
{reviewers}
*Please review PR.*
<{url}|{title}>


"""

no_pr="""\
There is no PR for review :)
*Great job, guys!*

"""


prs = []


def fetch_pr(repo_name, issue):
    pr_id = int(issue.pull_request.html_url.split("/")[-1])
    pr = issue.repository.get_pull(pr_id)
    prs.append((repo_name, pr))

def get_reviewers(assignee):
    if assignee is None:
        return list(git2slack.values()) + ["Please assign PR to the assignee"]

    return [slack for git, slack in git2slack.items() if git != assignee.login]

def generate_text(prs):
    if not prs:
        return slack_comment.format(prs=no_pr)

    prs_comment = ''
    for repo_name, pr in prs:
        reviewers = get_reviewers(pr.assignee)
        prs_comment += pr_comment.format(reviewers=' '.join(reviewers),
                                            url=pr.html_url,
                                            title=pr.title)
    return slack_comment.format(prs=prs_comment)

def filter_issues(issues):
    for issue in issues:
        if issue.pull_request is None:
            continue
        if "WIP" not in [l.name for l in issue.labels]:
            yield issue

def post_slack(url, text):
    data = dict(channel=channel, username=username,
            text=text, link_names=1, mrkdwn=True)
    data = json.dumps(data)
    urllib.urlopen(url, str.encode(data))

def review_reminder():
    g = Github(token)
    repo_issue_prs = {}
    threads = []
    org = g.get_organization(org_name)
    git_repos ={repo: org.get_repo(repo) for repo in repos}

    for repo_name, repo in git_repos.items():
        issues = repo.get_issues(state='open')
        repo_issue_prs[repo_name] = filter_issues(issues)

    for repo_name, issues in repo_issue_prs.items():
        for issue in issues:
            t = threading.Thread(target=fetch_pr, args=(repo_name, issue))
            threads.append(t)
            t.start()

    for t in threads:
        t.join()

    text = generate_text(prs)
    post_slack(web_hook_url, text)
    return text

def lambda_handler(event, context):
    return review_reminder()
