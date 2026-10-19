# /verify
Run the full verification loop and report results honestly.
1. `docker compose up -d --build` and confirm all services are healthy.
2. Run backend tests and lint. Run frontend lint and tests.
3. Hit `/health` and one authenticated endpoint with curl.
4. Open the frontend in the browser and confirm the main page loads without console errors.
5. Summarise: what passed, what failed, what was not checked. Do not claim success without evidence.
