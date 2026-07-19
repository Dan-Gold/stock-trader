{{/*
Expand the name of the chart.
*/}}
{{- define "stock-trader.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "stock-trader.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "stock-trader.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "stock-trader.labels" -}}
helm.sh/chart: {{ include "stock-trader.chart" . }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/part-of: {{ include "stock-trader.name" . }}
{{- end }}

{{/*
Selector labels for a specific component.
Usage: {{ include "stock-trader.selectorLabels" (dict "context" . "component" "api") }}
*/}}
{{- define "stock-trader.selectorLabels" -}}
app.kubernetes.io/name: {{ include "stock-trader.name" .context }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Resolve the PostgreSQL host.
If config.db.host is set, use it; otherwise derive from the self-hosted
postgres Service name (see postgres-service.yaml).
*/}}
{{- define "stock-trader.dbHost" -}}
{{- if .Values.config.db.host }}
{{- .Values.config.db.host }}
{{- else if .Values.postgres.enabled }}
{{- printf "%s-postgres" (include "stock-trader.fullname" .) }}
{{- else }}
{{- fail "config.db.host is required when postgres.enabled=false (shared-infra deploy must point at the shared Postgres server)" }}
{{- end }}
{{- end }}

{{/*
Resolve the Redis host.
If config.redis.host is set, use it; otherwise derive from the self-hosted
redis Service name (see redis-service.yaml).
*/}}
{{- define "stock-trader.redisHost" -}}
{{- if .Values.config.redis.host }}
{{- .Values.config.redis.host }}
{{- else if .Values.redis.enabled }}
{{- printf "%s-redis" (include "stock-trader.fullname" .) }}
{{- else }}
{{- fail "config.redis.host is required when redis.enabled=false (shared-infra deploy must point at the shared Redis server)" }}
{{- end }}
{{- end }}

{{/*
Common environment variables (injected into every workload via envFrom).
Returns the envFrom block referencing ConfigMap + Secret.
*/}}
{{- define "stock-trader.envFrom" -}}
- configMapRef:
    name: {{ include "stock-trader.fullname" . }}-config
- secretRef:
    name: {{ include "stock-trader.fullname" . }}-secret
{{- end }}
