/**
 * API client for Forecast endpoints.
 */

import { apiFetch } from './client'

export interface ForecastPoint {
  date: string
  predicted_qty: number
  lower_bound: number
  upper_bound: number
}

export interface ForecastSummary {
  product_id: string
  product_name: string
  sku: string
  from_date: string
  to_date: string
  avg_mape: number | null
  model_name: string
  last_trained: string
}

export interface ForecastResponse {
  product_id: string
  model_name: string
  mape: number | null
  rmse: number | null
  horizon_days: number
  forecasts: ForecastPoint[]
  shap_features: Record<string, number>
  from_cache: boolean
  error?: string
}

export interface ForecastListResponse {
  forecasts: ForecastSummary[]
  total: number
}

export function fetchForecastList(limit = 30): Promise<ForecastListResponse> {
  return apiFetch(`/forecast/?limit=${limit}`)
}

export function fetchForecast(productId: string, horizon = 30): Promise<ForecastResponse> {
  return apiFetch(`/forecast/${productId}?horizon=${horizon}`)
}
