/**
 * Contracts shared between the web app and the API.
 *
 * These mirror the Pydantic schemas in `apps/api/app/`. When a schema changes on
 * one side, change it here too — this package is the single place the two apps
 * agree on a shape.
 */

export * from "./types/system";
export * from "./types/evidence";
