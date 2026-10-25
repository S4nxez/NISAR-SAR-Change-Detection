# DevOps Roadmap

## Instructions

- Execute **one roadmap item per pull request**, following logical dependency order rather than the order in which items are listed.
- Before starting an item, inspect the current codebase, infrastructure and existing roadmap items to identify dependencies, blockers and prerequisites.
- Prioritize foundational work before dependent features. For example, create a resource before implementing functionality that uses it.
- Among items that are ready to implement, prioritize by product impact, reliability, security and operational value.
- Implement only one roadmap item per PR. Do not bundle unrelated items or silently expand the scope.
- If an item depends on unfinished work, skip it temporarily and select the next highest-priority item whose dependencies are satisfied.
- If an item is ambiguous, investigate the existing project and make reasonable decisions consistent with its architecture. Ask for clarification only when a significant decision cannot be made safely.
- Follow existing project conventions and minimize unnecessary changes. Do not rewrite unrelated code or infrastructure.
- Run the relevant tests and validation checks before opening a PR. Include any necessary tests and documentation in the same PR.
- After completing an item, update this roadmap to mark it as done and record the associated PR. Commit the roadmap update in the same PR when practical.
- Never mark an item as complete unless its implementation and relevant validation have succeeded.
- If blocked, document the reason and continue with another independent, actionable item.

## Roadmap

- [ ] - <impact 0/10> **[Short task title]** — Describe the desired outcome and relevant scope.

- [ ] - <6> **[Create develop flux]** — Clone the existing flux for the develop branch, making prod (existing) more resistent as developers will have a previous deployment to do QA
- [ ] - <8> **[Create a pre-deployment validation stage]** — Implement a CI/CD pipeline stage that validates every project before allowing deployment to proceed. It must run all available unit and integration tests, verify that each project compiles and builds successfully, and perform startup checks to detect runtime configuration issues, Spring initialization failures, database connectivity errors, and other critical errors that could prevent the application from running correctly. Fail the pipeline if any required check fails, preventing invalid builds from reaching deployment. Reuse the existing project tooling and pipeline conventions wherever possible, and ensure the stage provides clear, actionable failure logs.
- [ ] - <9> [Add post-deployment smoke tests] — After each deployment, automatically verify that the deployed application is reachable, the backend starts correctly, the database connection works, and the frontend can successfully communicate with the backend. Fail the deployment workflow if critical checks fail, and provide clear logs identifying the failure. Reuse existing endpoints and tooling wherever possible.
- [ ] - <10> [Implement a safe production rollback] — Ensure that a failed or faulty deployment can be reverted quickly to the last known-good application images without requiring a manual rebuild. Preserve the existing production data, avoid disrupting unrelated containers and services on the Raspberry Pi, and document the simplest reliable recovery procedure.


## Project Constraints

- Preserve existing functionality unless a roadmap item explicitly requires changing it.
- Keep changes focused, maintainable and consistent with the current architecture.
- Never commit secrets, credentials or environment-specific sensitive data.
- Do not introduce new infrastructure, dependencies or services unless required by the task or explicitly justified.
- Treat successful tests, builds and deployment checks as requirements where applicable.

## Completed

<!-- Move completed items here to retain a history. -->
