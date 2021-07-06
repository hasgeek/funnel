Instructions to run frontend tests written in Cypress test runner in development.

1. Add these environment variables to `secrets.test`:
   export RECAPTCHA_PUBLIC_KEY=''
   export RECAPTCHA_PRIVATE_KEY=''
   export CYPRESS_BOXOFFICE_SECRET_KEY=''
   export CYPRESS_BOXOFFICE_ACCESS_KEY=''
   export CYPRESS_BOXOFFICE_IC_ID=''
   export CYPRESS_BOXOFFICE_CLIENT_ID=''
   export GOOGLE_MAPS_API_KEY=''
   export YOUTUBE_API_KEY=''
   export VIMEO_CLIENT_ID=''
   export VIMEO_CLIENT_SECRET=''
   export VIMEO_ACCESS_TOKEN=''
2. Create test db 'funnel_testing'
3. Run runfrontendtests.sh to start server and execute Cypress test cases.
