{{/*
Compatibility helpers for Claude 3.5 migration
*/}}

{{/*
Get the appropriate model based on legacy mode setting
*/}}
{{- define "kubeintel.model" -}}
{{- if .Values.config.strands.legacyMode -}}
{{- .Values.config.strands.legacyModel | default "anthropic.claude-3-haiku-20240307-v1:0" -}}
{{- else -}}
{{- .Values.config.strands.model -}}
{{- end -}}
{{- end -}}

{{/*
Get the appropriate fallback model
*/}}
{{- define "kubeintel.fallbackModel" -}}
{{- if .Values.config.strands.legacyMode -}}
{{- .Values.config.strands.legacyModel | default "anthropic.claude-3-haiku-20240307-v1:0" -}}
{{- else -}}
{{- .Values.config.strands.fallbackModel | default "anthropic.claude-3-5-haiku-20241022-v1:0" -}}
{{- end -}}
{{- end -}}

{{/*
Get session TTL with backward compatibility
*/}}
{{- define "kubeintel.sessionTtl" -}}
{{- if .Values.config.strands.legacyMode -}}
{{- .Values.config.strands.sessionTtl | default 3600 -}}
{{- else -}}
{{- .Values.config.strands.sessionTtl | default 7200 -}}
{{- end -}}
{{- end -}}

{{/*
Check if Claude 3.5 features should be enabled
*/}}
{{- define "kubeintel.isClaude35" -}}
{{- not .Values.config.strands.legacyMode -}}
{{- end -}}

{{/*
Generate model-specific annotations
*/}}
{{- define "kubeintel.modelAnnotations" -}}
{{- if .Values.config.strands.legacyMode }}
kubeintel.io/model-version: "claude-3"
kubeintel.io/model-type: "legacy"
{{- else }}
kubeintel.io/model-version: "claude-3.5"
kubeintel.io/model-type: "enhanced"
{{- end }}
kubeintel.io/primary-model: {{ include "kubeintel.model" . | quote }}
kubeintel.io/fallback-model: {{ include "kubeintel.fallbackModel" . | quote }}
{{- end -}}

{{/*
Validate configuration and return warnings
*/}}
{{- define "kubeintel.validateConfig" -}}
{{- $warnings := list -}}

{{/* Check session TTL */}}
{{- if lt (.Values.config.strands.sessionTtl | int) 3600 -}}
{{- $warnings = append $warnings "Session TTL is below recommended minimum (3600s)" -}}
{{- end -}}

{{/* Check Claude 3.5 specific settings */}}
{{- if not .Values.config.strands.legacyMode -}}
  {{/* Check if model is actually Claude 3.5 */}}
  {{- if not (contains "claude-3-5" .Values.config.strands.model) -}}
  {{- $warnings = append $warnings "Primary model is not Claude 3.5 but legacy mode is disabled" -}}
  {{- end -}}
  
  {{/* Check streaming is disabled */}}
  {{- if not .Values.config.strands.disableStreaming -}}
  {{- $warnings = append $warnings "Streaming should be disabled for Claude 3.5 compatibility" -}}
  {{- end -}}
  
  {{/* Check session TTL for Claude 3.5 */}}
  {{- if lt (.Values.config.strands.sessionTtl | int) 7200 -}}
  {{- $warnings = append $warnings "Session TTL below Claude 3.5 recommended value (7200s)" -}}
  {{- end -}}
{{- end -}}

{{/* Check resource limits */}}
{{- if .Values.resources.limits.memory -}}
  {{- $memLimit := .Values.resources.limits.memory -}}
  {{- if and (hasSuffix "Mi" $memLimit) (lt (trimSuffix "Mi" $memLimit | int) 1024) -}}
  {{- $warnings = append $warnings "Memory limit may be too low for Claude 3.5 workloads" -}}
  {{- end -}}
{{- end -}}

{{/* Return warnings as comma-separated string */}}
{{- if $warnings -}}
{{- join ", " $warnings -}}
{{- end -}}
{{- end -}}

{{/*
Generate environment variables for model configuration
*/}}
{{- define "kubeintel.modelEnvVars" -}}
- name: AGENT_STRANDS_MODEL
  value: {{ include "kubeintel.model" . | quote }}
- name: AGENT_STRANDS_FALLBACK_MODEL
  value: {{ include "kubeintel.fallbackModel" . | quote }}
- name: AGENT_STRANDS_SESSION_TTL
  value: {{ include "kubeintel.sessionTtl" . | quote }}
- name: AGENT_LEGACY_MODE
  value: {{ .Values.config.strands.legacyMode | quote }}
- name: AGENT_CLAUDE35_ENABLED
  value: {{ include "kubeintel.isClaude35" . | quote }}
{{- end -}}