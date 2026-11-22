# Security policy

## Supported versions

Only the latest `main` is supported. There are no releases yet.

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report it privately via GitHub instead: **Security → Report a vulnerability**
([direct link](../../security/advisories/new)). You will get an answer within a few days.
This is a hobby project maintained in spare time, so please allow some time for a fix.

## Scope

This project runs locally and talks to a LEGO Move Hub over Bluetooth LE. Relevant reports
are, for example, problems in our code or CI workflows, or a vulnerable dependency we pin.
Weaknesses of the LEGO hub firmware or the Bluetooth LE protocol itself are out of scope;
please report those to LEGO or the upstream projects (pylgbst, bleak).
