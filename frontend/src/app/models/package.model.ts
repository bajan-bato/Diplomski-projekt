/** Application-facing model for a PACKAGE row. Field names mirror the database/API contract exactly. */
export interface Package {
  packageId: string;
  title: string;
  description: string;
  url: string;
}
