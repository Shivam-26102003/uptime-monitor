export interface UrlStatus {
  id: number;
  url: string;
  is_up: boolean | null;
  status_code: number | null;
  response_time_ms: number | null;
  last_checked: string | null;
}
