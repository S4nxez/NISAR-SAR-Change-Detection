# DevOps Roadmap

<!--
Item format: - [ ] - <impact 0-10> **[Short task title]** — Desired outcome and relevant scope.
Agent rules: tools/roadmap-agent/AGENT.md (the agent only moves finished items to Completed).
Optional: add a "## Context" section with notes specific to this roadmap.
-->

## Roadmap

- [ ] - <6> **[Create develop flux]** — Clone the existing flux for the develop branch, making prod (existing) more resistent as developers will have a previous deployment to do QA
- [ ] - <8> **[Create a pre-deployment validation stage]** — Implement a CI/CD pipeline stage that validates every project before allowing deployment to proceed. It must run all available unit and integration tests, verify that each project compiles and builds successfully, and perform startup checks to detect runtime configuration issues, Spring initialization failures, database connectivity errors, and other critical errors that could prevent the application from running correctly. Fail the pipeline if any required check fails, preventing invalid builds from reaching deployment. Reuse the existing project tooling and pipeline conventions wherever possible, and ensure the stage provides clear, actionable failure logs.
- [ ] - <9> [Add post-deployment smoke tests] — After each deployment, automatically verify that the deployed application is reachable, the backend starts correctly, the database connection works, and the frontend can successfully communicate with the backend. Fail the deployment workflow if critical checks fail, and provide clear logs identifying the failure. Reuse existing endpoints and tooling wherever possible.
- [ ] - <10> [Implement a safe production rollback] — Ensure that a failed or faulty deployment can be reverted quickly to the last known-good application images without requiring a manual rebuild. Preserve the existing production data, avoid disrupting unrelated containers and services on the Raspberry Pi, and document the simplest reliable recovery procedure.

## Completed

