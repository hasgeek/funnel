Instructions to run frontend tests written in Cypress test runner in development.

1. Add Users and Organisation to development lastuser
	In the development lastuser, create an admin and member user.
	Create an organisation "testcypressproject" and add admin user to the owners team.
	Add the login credentials details of admin and member user as environment variables. During the test execution to login, these values are read from fixture file user.js.
	These are the environment variables to be created.
	i) CYPRESS_ADMIN_USERNAME
    ii) CYPRESS_ADMIN_PSW
    iii) CYPRESS_MEMBER_USERNAME
    iv) CYPRESS_MEMBER_PSW

2. Add the following details of testing.py config as environment variables or update the values in testing.py file.
	i) LASTUSER_SERVER
	ii) LASTUSER_CLIENT_ID
	iii) LASTUSER_CLIENT_SECRET
	iv) RECAPTCHA_PUBLIC_KEY
	v) RECAPTCHA_PRIVATE_KEY

3. Get the record keys from the cypress dashboard(https://dashboard.cypress.io/) and add as environment variable 'RECORD_KEY'. This is used in runfrontendtests.sh to record test results, screenshots and videos in Cypress.

4. Run runfrontendtests.sh to start server and execute Cypress test cases.
