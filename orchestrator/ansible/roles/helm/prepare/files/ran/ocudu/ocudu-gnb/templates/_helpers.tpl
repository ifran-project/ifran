{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "ocudu-gnb.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "ocudu-gnb.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "ocudu-gnb.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "ocudu-gnb.labels" -}}
helm.sh/chart: {{ include "ocudu-gnb.chart" . }}
{{ include "ocudu-gnb.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "ocudu-gnb.selectorLabels" -}}
app.kubernetes.io/name: {{ include "ocudu-gnb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "ocudu-gnb.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "ocudu-gnb.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Count enabled interfaces with defaultRoute defined and non-empty
*/}}
{{- define "ocudu-gnb.countDefaultRouteInterfaces" -}}
{{- $count := 0 -}}
{{- if and .Values.multus.enabled (gt (len .Values.multus.interfaces) 0) -}}
  {{- range $i, $if := .Values.multus.interfaces }}
    {{- if $if.enabled }}
      {{- if (not (empty $if.defaultRoute)) }}
        {{- $count = add $count 1 }}
      {{- end }}
    {{- end }}
  {{- end }}
{{- end }}
{{- $count -}}
{{- end }}

{{/*
Resolve N2 interface name
- Uses enabled: true check
- Falls back to N3 if N2 is disabled or missing
- Defaults to eth0
*/}}
{{- define "ocudu-gnb.n2IfName" -}}
{{- if not .Values.multus.enabled -}}
eth0
{{- else -}}
  {{- $n2 := "" -}}
  {{- $n3 := "" -}}
  {{- range $if := .Values.multus.interfaces }}
    {{- if and (eq $if.name "n2") $if.enabled }}{{- $n2 = $if.name -}}{{- end -}}
    {{- if and (eq $if.name "n3") $if.enabled }}{{- $n3 = $if.name -}}{{- end -}}
  {{- end -}}
  {{- if $n2 -}}
{{ $n2 }}
  {{- else if $n3 -}}
{{ $n3 }}
  {{- else -}}
eth0
  {{- end -}}
{{- end -}}
{{- end }}


{{/*
Resolve N3 interface name
- Uses enabled: true check
- Falls back to N2 if N3 is disabled or missing
- Defaults to eth0
*/}}
{{- define "ocudu-gnb.n3IfName" -}}
{{- if not .Values.multus.enabled -}}
eth0
{{- else -}}
  {{- $n2 := "" -}}
  {{- $n3 := "" -}}
  {{- range $if := .Values.multus.interfaces }}
    {{- if and (eq $if.name "n2") $if.enabled }}{{- $n2 = $if.name -}}{{- end -}}
    {{- if and (eq $if.name "n3") $if.enabled }}{{- $n3 = $if.name -}}{{- end -}}
  {{- end -}}
  {{- if $n3 -}}
{{ $n3 }}
  {{- else if $n2 -}}
{{ $n2 }}
  {{- else -}}
eth0
  {{- end -}}
{{- end -}}
{{- end }}


{{/*
Resolve E2 interface name using `name` field
*/}}
{{- define "ocudu-gnb.e2IfName" -}}
{{- if and .Values.multus.enabled (gt (len .Values.multus.interfaces) 3) (hasKey (index .Values.multus.interfaces 3) "name") -}}
{{ (index .Values.multus.interfaces 3).name }}
{{- else -}}
eth0
{{- end -}}
{{- end }}
