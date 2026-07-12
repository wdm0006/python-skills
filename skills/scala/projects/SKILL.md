---
name: building-scala-projects
description: Sets up, tests, and publishes Scala projects — sbt build layout, scalafmt/scalafix as CI gates, Scala 2-vs-3 and cross-building, a test job that actually runs, and Maven Central publishing via sbt-ci-release. Use when creating an sbt project, wiring GitHub Actions for Scala, debugging a cross-build or scalafmt CI failure, or preparing a Sonatype/Maven Central release.
---

# Building Scala Projects

> Starting point. This skill captures the load-bearing sbt/Scala conventions;
> extend it with reference files (a full `build.sbt`, a CI workflow, a publish
> runbook) as the patterns firm up, following the same one-owner discipline as the
> Python skills.

Scala's failure modes cluster around the build tool and cross-versioning: a JVM
or Scala version that differs between laptop and CI, a cross-build that only
compiles one axis, and a publish step that half-completes on Sonatype. The rules
below keep the gate honest.

## build.sbt essentials

```scala
ThisBuild / scalaVersion := "3.3.4"          // pin; 3.3.x is the current LTS
ThisBuild / organization := "com.example"

lazy val root = (project in file("."))
  .settings(
    name := "my-lib",
    libraryDependencies ++= Seq(
      "org.scalameta" %% "munit" % "1.0.0" % Test
    ),
    // fail the build on warnings in CI-critical code
    scalacOptions ++= Seq("-deprecation", "-feature", "-Wunused:all")
  )
```

Pin the JVM too — an `.sbtopts`/`.java-version` or `setup-java` matrix that
differs from local is a common source of "works on my machine." Use `%%` (not
`%`) for Scala libraries so the Scala-version suffix is appended automatically.

## The CI gate: format + lint + test on a pinned JVM

```yaml
- uses: actions/setup-java@v4
  with: { distribution: temurin, java-version: '21' }   # pin, not "latest"
- run: sbt scalafmtCheckAll        # formatting is a gate
- run: sbt "scalafixAll --check"   # lint/rewrite rules, check-only in CI
- run: sbt test
```

`scalafmtCheckAll` and `scalafixAll --check` must run the **same** rules as the
local `sbt scalafmt`/`scalafix` — pin `scalafmt` in `.scalafmt.conf` (with a
`version = "x.y.z"` line) so a runner installing a newer formatter can't reformat
untouched files and turn a `--check` gate red on an unrelated PR.

## Cross-building: compile every axis you claim to support

`crossScalaVersions` is a promise that all listed versions compile and test. If
CI only runs the default `scalaVersion`, the others rot silently.

```scala
ThisBuild / crossScalaVersions := Seq("2.13.14", "3.3.4")
```

Run the whole cross-build in CI with the `+` prefix — `sbt +test` — or a matrix
cell per version. Scala 2 and Scala 3 differ in syntax and macros, so code that
compiles on 3 can fail on 2.13 (and vice versa); test both or drop the axis from
`crossScalaVersions` rather than advertise coverage you don't have.

## A test job that runs nothing is a no-op gate

`sbt test` exits 0 when a module has no tests. As with any language, confirm the
test job executes assertions — MUnit/ScalaTest print a test count; assert on it in
review rather than trusting a green check. Put pure logic (parsers, encoders,
state transitions) in testable functions and cover them first.

## Publishing to Maven Central

Maven Central publishing is multi-step and easy to leave half-done (staged but
never released, or missing the required POM metadata / GPG signature). Automate it
with **sbt-ci-release**, which handles snapshot-vs-release routing, signing, and
Sonatype bundle release from a tag:

```scala
// project/plugins.sbt
addSbtPlugin("com.github.sbt" % "sbt-ci-release" % "1.x.y")
```

Required for Central: `licenses`, `developers`, `scmInfo`, and a source+javadoc
jar — sbt-ci-release wires most of it, but a missing `developers`/`scmInfo` block
fails validation *after* upload. Do a snapshot publish first to shake out metadata
errors before cutting a real tag. Central versions are immutable — never reuse a
released version number.

## Checklist

```
Scala project health:
- [ ] scalaVersion and JVM (setup-java) pinned; local == CI
- [ ] .scalafmt.conf has a pinned version = line
- [ ] CI runs scalafmtCheckAll, scalafix --check, and test
- [ ] crossScalaVersions all compiled+tested in CI (+test or a matrix), or trimmed
- [ ] test job actually runs assertions (not a zero-test no-op)
- [ ] %% used for Scala deps so the version suffix is applied
- [ ] Maven Central metadata complete: licenses, developers, scmInfo, source+javadoc
- [ ] snapshot published once before the first real release; versions never reused
```
