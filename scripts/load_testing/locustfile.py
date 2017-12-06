import os
import pdb
from random import randint

from faker import Factory
import locust
import pyquery

import foney

fake = Factory.create()
phone_numbers = foney.phone_numbers()

username, password = os.getenv('AUTH_USER'), os.getenv('AUTH_PASS')
auth = (username, password) if username and password else ()

# This should match however many users were created
# for the DB by the rake task.
NUM_USERS = 100

def random_cred():
    """
    Given the rake task:
    rake dev:random_users NUM_USERS=100 SCRYPT_COST='800$8$1$'

    We should have 100 existing users with credentials matching:
    * email address testuser1@example.com through testuser1000@example.com
    * the password "salty pickles"
    * a phone number between +1 (415) 555-0001 and +1 (415) 555-1000.

    This will generate a set of credentials to match one of those entries.
    Note that YOU MUST run the rake task to put these users in the DB first.

    """
    return {
        'email': 'testuser{}@example.com'.format(randint(1, NUM_USERS-1)),
        'password': "salty pickles"
    }

def authenticity_token(dom):
    """
    Retrieves the CSRF auth token from the DOM for submission
    """
    return dom.find('input[name="authenticity_token"]:first').attr('value')

def login(t, credentials):
    """
    Takes a locustTask object and signs you in.
    """

    # ensure we're at sign-in page and submit credentials
    resp = t.client.get('/', catch_response=True)
    resp.raise_for_status()
    
    # If you're already logged in, it'll redirect to /account.
    # We need to handle this, or you'll get all sorts of downstream failures.
    if '/account' in resp.url:
        print("You appear to be already logged in. We're going to quit login().")
        return resp

    dom = pyquery.PyQuery(resp.content)
    token = authenticity_token(dom)
    
    if not token or "Sign in" not in dom.text():
        resp.failure(
            """
            We don't appear to be on a sign-in page.
            Current URL is {}.
            """.format(resp.url)
        )
    
    resp = t.client.post(
        resp.url,
        catch_response=True,
        data = {
            'user[email]': credentials['email'],
            'user[password]': credentials['password'],
            'authenticity_token': authenticity_token(dom),
            'commit': 'Submit',
        },
    )
    resp.raise_for_status()
    
    dom = pyquery.PyQuery(resp.content)
    code = dom.find("#code").attr('value')
    if not code:
        # if we didn't seen the code, then we probably have a failed login 
        # un-reset credentials. So let's try to rescue with the other pass.
        print("we didn't see a 2FA code. Trying again, with {} posting to {}".format(
            credentials,
            resp.url
            )
        )
        resp = t.client.post(
            resp.url,
            catch_response=True,
            data = {
                'user[email]': credentials['email'],
                'user[password]': 'thisisanewpass',
                'authenticity_token': authenticity_token(dom),
                'commit': 'Submit',
            }
        )
        resp.raise_for_status()
        
        dom = pyquery.PyQuery(resp.content)
        code = dom.find("#code").attr('value')
        
        # If we still don't have code, we have a bigger problem.
        if not code:
            print("""
                No 2FA code found after two tries. 
                Make sure {} is in the DB
                """.format(credentials)
            )
            resp.failure("No 2FA code on {} using .".format(resp.url, credentials))
            return

    code_form = dom.find("form[action='/login/two_factor/sms']")
    resp = t.client.post(
        code_form.attr('action'),
        data = {
            'code': code,
            'authenticity_token': authenticity_token(dom),
            'commit': 'Submit'
        }
    )
    
    # We're not checking for post-login state here, 
    # as it will vary depending on the SP.
    resp.raise_for_status()
    return resp

def logout(t):
    """
    Takes a locustTask object and signs you out.
    Naively assumes the user is actually logged in already.
    """
    resp = t.client.get(
        '/',
        catch_response=True
    )
    resp.raise_for_status()
    dom = pyquery.PyQuery(resp.content)
    sign_out_link = dom.find('a[href="/api/saml/logout"]').attr('href')
    if not sign_out_link:
        resp.failure("No signout link at {}.".format(resp.url))
        return
    # Authentication is now complete.
    # We've confirmed by the presence of the sign-out link.
    # We can now have the person sign out.
    resp = t.client.get(sign_out_link)
    resp.raise_for_status()
    dom = pyquery.PyQuery(resp.content)


def change_pass(t, password):
    """
    Takes a locustTask and naively expects an already logged in person,
    this navigates to the account (which they should already be on, post-login)
    """

    resp = t.client.get('/account')
    resp.raise_for_status()
    dom = pyquery.PyQuery(resp.content)
    edit_link = dom.find('a[href="/manage/password"]')

    try:
        resp = t.client.get(edit_link[0].attrib['href'])
    except Exception as error:
        print("""
            There was a problem finding the edit pass link: {}
            Most likely, you're hitting an OTP cap with this user, 
            or did not run the rake task to generate users.
            Since we can't change the password, we'll exit.
            Here is the content we're seeing at {}: {}
            """.format(error, resp.url, dom('.container').eq(0).text())
        )
        return

    resp.raise_for_status()
    dom = pyquery.PyQuery(resp.content)
    # To keep it simple for now we're skipping reauth
    if '/manage/password' in resp.url:
        resp = t.client.post(
            resp.url,
            data = {
                'update_user_password_form[password]': password,
                'authenticity_token': authenticity_token(dom),
                '_method': 'patch',
                'commit': 'update'
            }
        )
        resp.raise_for_status()
    else:
        # To-do: handle reauthn case
        print("Failed to find correct page. Currently at {}".format(resp.url))

def signup(t, signup_url=None):
    """
    Creates a new account.
    """
    # start at home page,
    # then navigate to create account page and submit email
    # we're checking for signup_url to pass name and group results
    if signup_url:
        t.client.get(
            signup_url,
            auth=auth,
            name="/sign_up/start?request_id"
        )
    else:
        t.client.get('/sign_up/start', auth=auth)
    resp = t.client.get('/sign_up/enter_email', auth=auth)
    resp.raise_for_status()

    data = {
        'user[email]': 'test+' + fake.md5() + '@test.com',
        'authenticity_token': authenticity_token(pyquery.PyQuery(resp.content)),
        'commit': 'Submit',
    }
    resp = t.client.post(
        '/sign_up/enter_email',
        data=data,
        auth=auth
    )
    resp.raise_for_status()

    dom = pyquery.PyQuery(resp.content)
    try:
        link = dom.find("a[href*='confirmation_token']")[0].attrib['href']
    except IndexError:
        if '/account' in resp.url:
            print("""
                Account appears to already be signed up and logged in. 
                We're at {}.
                """.format(resp.url)
            )
        else: 
            print("""
                Failed to get confirmation token.
                Consult https://github.com/18F/identity-idp#load-testing
                and check your application config.

                We were at {} when we couldn't find it.
                """.format(resp.url)
            )
        return

    # Follow email confirmation link and submit password
    resp = t.client.get(
        link,
        auth=auth,
        name='/sign_up/email/confirm?confirmation_token='
    )
    resp.raise_for_status()

    dom = pyquery.PyQuery(resp.content)
    confirmation_token = dom.find('[name="confirmation_token"]')[0].attrib['value']
    data = {
        'password_form[password]': 'salty pickles',
        'authenticity_token': authenticity_token(dom),
        'confirmation_token': confirmation_token,
        'commit': 'Submit',
    }
    resp = t.client.post(
        '/sign_up/create_password', data=data, auth=auth
    )
    resp.raise_for_status()

    # visit phone setup page and submit phone number
    dom = pyquery.PyQuery(resp.content)
    data = {
        '_method': 'patch',
        'user_phone_form[international_code]': 'US',
        'user_phone_form[phone]': phone_numbers[randint(1,1000)],
        'user_phone_form[otp_delivery_preference]': 'sms',
        'authenticity_token': authenticity_token(dom),
        'commit': 'Send security code',
    }
    resp = t.client.post('/phone_setup', data=data, auth=auth)
    resp.raise_for_status()

    # visit security code page and submit pre-filled OTP
    dom = pyquery.PyQuery(resp.content)
    try:
        otp_code = dom.find('input[name="code"]')[0].attrib['value']
    except Exception as error:
        print("""
            There is a problem creating this account: {}. 
            Here is the response content: {}
            """.format(error, resp.content))
        return

    data = {
        'code': otp_code,
        'authenticity_token': authenticity_token(dom),
        'commit': 'Submit',
    }
    resp = t.client.post('/login/two_factor/sms', data=data, auth=auth)
    resp.raise_for_status()

    # click Continue on personal key page
    dom = pyquery.PyQuery(resp.content)
    data = {
        'authenticity_token': authenticity_token(dom),
        'commit': 'Continue',
    }
    t.client.post('/sign_up/personal_key', data=data, auth=auth)


class UserBehavior(locust.TaskSet):
    def on_start(self):
        pass

    @locust.task(1)
    def idp_change_pass(self):
        """
        Login, change pass, change it back and logout from IDP.

        This is given a very low weight, since we do not expect
        it to be a common pattern in the real world.
        """
        credentials = random_cred()
        login(self, credentials)
        change_pass(self, "thisisanewpass")
        # now change it back.
        change_pass(self, credentials['password'])
        logout(self)

    @locust.task(2)
    def sp_rails_change_pass(self):
        """
        Login, change pass, change it back and logout from
        sp-rails sample app.

        This is given a very low weight, since we do not expect
        it to be a common pattern in the real world.
        """
        resp = self.client.get('http://localhost:3003')
        resp.raise_for_status()
        dom = pyquery.PyQuery(resp.content)

        """
        # TO-DO: submit the LOA1/LOA3 form
        # We can't do this from form action yet, because there's a mismatch
        # in how we're handling the trailing slash on host in locust and elsewhere:
        # in requests/models.py", line 371, in prepare_url
        #     scheme, auth, host, port, path, query, fragment = parse_url(url)
        # results in localhost:3000auth rather than localhost:3000/auth/saml/
        # Until we get that sorted out, this will need to be commented out
        # and we'll manually go to the IPD url.

        resp = self.client.post(
            dom.find("form").eq(0).attr('action'),
            data = {
                'loa': 1,
                'authenticity_token': authenticity_token(dom)
            }
        )
        # For now, we're taking advantage of login() going to host + /sign_in
        """
        credentials = random_cred()
        login(self, credentials)
        change_pass(self, "thisisanewpass")
        # now change it back.
        change_pass(self, credentials['password'])
        logout(self)

    # rubocop:disable MethodLength
    @locust.task(70)
    def usajobs_change_pass(self):
        """
        Login, change pass, change it back and logout from USAjobs.

        This is most common task and is heavily weighted.

        We have disabled method linting because:
        1. It counts arguments as separate lines.
        2. This is how many steps it takes for the flow.
        """
        root_url = 'https://www.test.usajobs.gov'
        resp = self.client.get(
            root_url,
            catch_response=True
        )
        dom = pyquery.PyQuery(resp.content)
        signin_link = dom.find('a.user-logged-out[href="/Applicant/ProfileDashboard/Home"]:first')

        if not signin_link:
            resp.failure("We could not find a signin link at {}".format(resp.url))

        resp = self.client.get(
            root_url + signin_link[0].attrib['href'],
            catch_response=True
        )
        if resp.status_code is not 200:
            resp.failure(
                """
                We see a bad {} response code at {} with the headers {}. Response is:
                """.format(resp.status_code, resp.url, resp.headers, resp.content)
            )
        # we should have been redirected to
        # https://login.test.usajobs.gov/Access/Transition. Let's do a quick check.
        if resp.url is not "https://login.test.usajobs.gov/Access/Transition":
            resp.failure(
                """"
                We do not appear to have been redirected to 
                https://login.test.usajobs.gov/Access/Transition.
                Our current URL is {}, with content {}.
                """.format(resp.url, resp.content)
            )
        # Now that we've confirmed we're at the right URL
        # we need to POST to it, per USAjobs.
        resp = self.client.post(
            resp.url,
            catch_response=True,
            data = {},
            name="/Access/Transition"
        )
        # Check to make sure we redirected to our target host, 
        # with a request_id in resp.url
        if resp.url is not os.getenv('TARGET_HOST'):  
            resp.failure(
                """"
                We do not appear to have been redirected to the IDP host.
                Instead, we are at {}.
                """.format(resp.url)
            )
        credentials = random_cred()        
        login(self, credentials)
        change_pass(self, "thisisanewpass")
        # now change it back.
        change_pass(self, credentials['password'])
        logout(self)
    # rubocop:ensable MethodLength
    
    @locust.task(2)
    def idp_create_account(self):
        """
        Create an account from within the IDP.

        This is given a low weight because it's not common
        in the real world.
        """
        signup(self)
        logout(self)

    # rubocop:disable MethodLength
    @locust.task(25)
    def usajobs_create_account(self):
        """
        Create an account from within USAjobs test domain. 

        This is given a relatively low weight.
        It's much more common than account creation from within IDP
        but much lower than a simple login/logout.

        If the os env var "NO_LOGOUT" has been set, this will skip 
        the logout step to help show the load of many open sessions.

        We have disabled method linting because:
        1. It counts arguments as separate lines
        2. This is how many steps it takes for the flow.
        """
        resp = self.client.get('https://www.test.usajobs.gov/')
        resp.raise_for_status()
        resp = self.client.get(
            'https://www.test.usajobs.gov/Applicant/ProfileDashboard/Home',
            catch_response=True
        )
        if resp.status_code is not 200:
            print(
                "Bad {} response at {} with the headers {}: {}".format(
                    resp.status_code, resp.url, resp.headers, resp.content
                )
            )
            resp.raise_for_status()
        # A quick post is required to setup for the SP handshake.
        # We'll pass the response url to signup()
        resp = self.client.post(
            resp.url,
            catch_response=True,
            data = {},
            name="/Access/Transition (create)"
        )
        if resp.status_code is not 200:
            print(
                "Bad {} response at {} with the headers {}: {}".format(
                    resp.status_code, resp.url, resp.headers, resp.content
                )
            )
            resp.raise_for_status()
        signup(self, resp.url)
        
        # Unless we said not to, sign out now.
        if "NO_LOGOUT" in os.environ:
            print("Found 'NO_LOGOUT' in env vars. Skipping logout.")
        else:
            logout(self)
    # rubocop:ensable MethodLength


class WebsiteUser(locust.HttpLocust):
    task_set = UserBehavior
    min_wait = 50
    max_wait = 100
    host = os.getenv('TARGET_HOST') or 'http://localhost:3000'


if __name__ == '__main__':
    WebsiteUser().run()