/**
 * KubeIntel Flow Visualizer
 * Integrates with Strands Telemetry API to visualize agent flows
 */

class FlowVisualizer {
    constructor() {
        this.flows = {
            agent: [],
            monitor: []
        };
        this.traces = [];
        this.currentView = 'flows';
        this.autoRefreshEnabled = true;
        this.refreshInterval = 10000; // 10 seconds
        this.refreshTimer = null;
        this.selectedFlow = null;
        
        this.init();
    }

    init() {
        // Initialize Flow Visualizer
        this.setupEventListeners();
        this.startAutoRefresh();
        this.refreshFlows();
    }

    setupEventListeners() {
        // Auto refresh checkbox
        const autoRefreshCheckbox = document.getElementById('autoRefresh');
        if (autoRefreshCheckbox) {
            autoRefreshCheckbox.addEventListener('change', (e) => {
                this.toggleAutoRefresh(e.target.checked);
            });
        }

        // Refresh interval selector
        const refreshIntervalSelect = document.getElementById('refreshInterval');
        if (refreshIntervalSelect) {
            refreshIntervalSelect.addEventListener('change', (e) => {
                this.updateRefreshInterval(parseInt(e.target.value));
            });
        }

        // View mode selector
        const viewModeSelect = document.getElementById('viewMode');
        if (viewModeSelect) {
            viewModeSelect.addEventListener('change', (e) => {
                this.switchViewMode(e.target.value);
            });
        }

        // Trace type filter
        const traceTypeFilter = document.getElementById('traceTypeFilter');
        if (traceTypeFilter) {
            traceTypeFilter.addEventListener('change', (e) => {
                this.filterTraces(e.target.value);
            });
        }
    }

    async refreshFlows() {
        // Refresh flows data
        this.updateStatus('loading');
        
        try {
            if (this.currentView === 'flows') {
                // Fetch telemetry data from both agent and monitor
                const [agentFlows, monitorFlows] = await Promise.all([
                    this.fetchAgentFlows(),
                    this.fetchMonitorFlows()
                ]);

                this.flows.agent = agentFlows;
                this.flows.monitor = monitorFlows;

                this.updateTimelines();
            } else if (this.currentView === 'traces') {
                // Fetch traces
                const traces = await this.fetchTraces();
                this.traces = traces;
                this.updateTracesTimeline();
            }

            this.updateMetrics();
            this.updateStatus('active');

        } catch (error) {
            console.error('Error refreshing flows:', error);
            this.updateStatus('error');
        }
    }

    switchViewMode(mode = null) {
        if (mode) {
            this.currentView = mode;
        } else {
            const viewModeSelect = document.getElementById('viewMode');
            this.currentView = viewModeSelect ? viewModeSelect.value : 'flows';
        }

        const flowsView = document.getElementById('flowsView');
        const tracesView = document.getElementById('tracesView');

        if (this.currentView === 'traces') {
            if (flowsView) flowsView.style.display = 'none';
            if (tracesView) tracesView.style.display = 'grid';
            this.refreshFlows(); // Refresh to load traces
        } else {
            if (flowsView) flowsView.style.display = 'grid';
            if (tracesView) tracesView.style.display = 'none';
            this.refreshFlows(); // Refresh to load flows
        }
    }

    async filterTraces(flowType = null) {
        if (this.currentView !== 'traces') return;

        try {
            const traces = await this.fetchTraces(50, flowType);
            this.traces = traces;
            this.updateTracesTimeline();
        } catch (error) {
            console.error('Error filtering traces:', error);
        }
    }

    updateTracesTimeline() {
        const timeline = document.getElementById('tracesTimeline');
        if (!timeline) return;

        timeline.innerHTML = '';

        if (this.traces.length === 0) {
            timeline.innerHTML = '<p style="color: #6c757d; text-align: center; margin-top: 50px;">No traces available</p>';
            return;
        }

        this.traces.forEach(trace => {
            const item = this.createTraceTimelineItem(trace);
            timeline.appendChild(item);
        });
    }

    createTraceTimelineItem(trace) {
        const item = document.createElement('div');
        item.className = `timeline-item ${trace.status === 'error' ? 'error' : ''}`;
        item.style.cursor = 'pointer';
        
        const statusClass = trace.status === 'success' ? '' : 'error';
        const duration = this.formatDuration(trace.duration);
        const timeAgo = this.formatTimeAgo(new Date(trace.startTime));
        
        const title = `${trace.type === 'agent_analysis' ? '🤖 Agent' : '📡 Monitor'} Trace - ${trace.status}`;
        const spansCount = trace.spans ? trace.spans.length : 0;
        const details = `Trace: ${trace.name}
Duration: ${duration} | Spans: ${spansCount}
Flow: ${trace.flow_id}`;

        item.innerHTML = `
            <div class="timeline-dot ${statusClass}"></div>
            <div class="timeline-content">
                <div class="timeline-time">${timeAgo}</div>
                <div class="timeline-title">${title}</div>
                <div class="timeline-details">${details}</div>
            </div>
        `;

        item.addEventListener('click', () => {
            this.showTraceDetails(trace.trace_id);
        });

        return item;
    }

    async fetchAgentFlows() {
        try {
            // Fetch recent analysis requests and their telemetry
            const response = await fetch('/api/telemetry/agent-flows', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                // Fallback to mock data if endpoint doesn't exist yet
                return this.generateMockAgentFlows();
            }

            const data = await response.json();
            return data.flows || [];
        } catch (error) {
            console.warn('Agent flows endpoint not available, using mock data:', error);
            return this.generateMockAgentFlows();
        }
    }

    async fetchMonitorFlows() {
        try {
            // Fetch background monitor telemetry
            const response = await fetch('/api/telemetry/monitor-flows', {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                // Fallback to mock data if endpoint doesn't exist yet
                return this.generateMockMonitorFlows();
            }

            const data = await response.json();
            return data.flows || [];
        } catch (error) {
            console.warn('Monitor flows endpoint not available, using mock data:', error);
            return this.generateMockMonitorFlows();
        }
    }

    async fetchTraces(limit = 50, flowType = null) {
        try {
            let url = `/api/telemetry/traces?limit=${limit}`;
            if (flowType) {
                url += `&flow_type=${flowType}`;
            }

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.warn('Traces endpoint not available');
                return [];
            }

            const data = await response.json();
            return data.traces || [];
        } catch (error) {
            console.warn('Traces endpoint not available:', error);
            return [];
        }
    }

    async fetchTraceById(traceId) {
        try {
            const response = await fetch(`/api/telemetry/traces/${traceId}`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                console.warn(`Trace ${traceId} not found`);
                return null;
            }

            const data = await response.json();
            return data.trace || null;
        } catch (error) {
            console.warn(`Failed to fetch trace ${traceId}:`, error);
            return null;
        }
    }

    generateMockAgentFlows() {
        const now = new Date();
        const flows = [];
        
        for (let i = 0; i < 5; i++) {
            const startTime = new Date(now.getTime() - (i * 60000) - Math.random() * 300000);
            const duration = 15000 + Math.random() * 45000; // 15-60 seconds
            const endTime = new Date(startTime.getTime() + duration);
            
            flows.push({
                id: `agent-flow-${Date.now()}-${i}`,
                type: 'agent_analysis',
                status: Math.random() > 0.1 ? 'completed' : 'error',
                startTime: startTime.toISOString(),
                endTime: endTime.toISOString(),
                duration: duration,
                request: this.getRandomAnalysisRequest(),
                tools: this.generateMockToolCalls(),
                model: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                tokens: {
                    input: Math.floor(1000 + Math.random() * 3000),
                    output: Math.floor(500 + Math.random() * 2000)
                },
                metadata: {
                    scope: Math.random() > 0.5 ? 'cluster' : 'namespace',
                    namespace: Math.random() > 0.5 ? 'default' : 'kube-system'
                }
            });
        }
        
        return flows.sort((a, b) => new Date(b.startTime) - new Date(a.startTime));
    }

    generateMockMonitorFlows() {
        const now = new Date();
        const flows = [];
        
        for (let i = 0; i < 8; i++) {
            const startTime = new Date(now.getTime() - (i * 180000) - Math.random() * 120000); // Every ~3 minutes
            const duration = 45000 + Math.random() * 75000; // 45-120 seconds
            const endTime = new Date(startTime.getTime() + duration);
            
            flows.push({
                id: `monitor-flow-${Date.now()}-${i}`,
                type: 'background_monitor',
                status: Math.random() > 0.05 ? 'completed' : 'timeout',
                startTime: startTime.toISOString(),
                endTime: endTime.toISOString(),
                duration: duration,
                cycle: i + 1,
                tools: this.generateMockMonitorToolCalls(),
                model: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                tokens: {
                    input: Math.floor(2000 + Math.random() * 4000),
                    output: Math.floor(1000 + Math.random() * 3000)
                },
                insights: {
                    anomalies: Math.floor(Math.random() * 3),
                    warnings: Math.floor(Math.random() * 5),
                    recommendations: Math.floor(1 + Math.random() * 4)
                }
            });
        }
        
        return flows.sort((a, b) => new Date(b.startTime) - new Date(a.startTime));
    }

    getRandomAnalysisRequest() {
        const requests = [
            'Provide comprehensive cluster health analysis',
            'Check pod status and identify failing pods',
            'Analyze resource usage and capacity',
            'Review recent events and their impact',
            'Examine namespace-specific issues',
            'Investigate deployment failures'
        ];
        return requests[Math.floor(Math.random() * requests.length)];
    }

    generateMockToolCalls() {
        const tools = [
            { name: 'execute_bash', command: 'kubectl get nodes -o wide', duration: 1200 },
            { name: 'execute_bash', command: 'kubectl get pods --all-namespaces', duration: 2300 },
            { name: 'execute_bash_batch', commands: 3, duration: 4500 },
            { name: 'fs_read', file: '/tmp/cluster-analysis.yaml', duration: 800 }
        ];
        
        const numTools = 2 + Math.floor(Math.random() * 3);
        return tools.slice(0, numTools);
    }

    generateMockMonitorToolCalls() {
        return [
            { name: 'execute_bash_batch', commands: 7, duration: 8500 },
            { name: 'execute_bash', command: 'kubectl get events --sort-by=.lastTimestamp', duration: 3200 },
            { name: 'execute_bash', command: 'kubectl top nodes', duration: 1800 },
            { name: 'fs_write', file: '/tmp/monitoring-cycle.json', duration: 600 }
        ];
    }

    updateTimelines() {
        this.updateAgentTimeline();
        this.updateMonitorTimeline();
    }

    updateAgentTimeline() {
        const timeline = document.getElementById('agentFlowTimeline');
        if (!timeline) return;

        timeline.innerHTML = '';

        if (this.flows.agent.length === 0) {
            timeline.innerHTML = '<p style="color: #6c757d; text-align: center; margin-top: 50px;">No agent flows available</p>';
            return;
        }

        this.flows.agent.forEach(flow => {
            const item = this.createTimelineItem(flow, 'agent');
            timeline.appendChild(item);
        });
    }

    updateMonitorTimeline() {
        const timeline = document.getElementById('monitorFlowTimeline');
        if (!timeline) return;

        timeline.innerHTML = '';

        if (this.flows.monitor.length === 0) {
            timeline.innerHTML = '<p style="color: #6c757d; text-align: center; margin-top: 50px;">No monitor flows available</p>';
            return;
        }

        this.flows.monitor.forEach(flow => {
            const item = this.createTimelineItem(flow, 'monitor');
            timeline.appendChild(item);
        });
    }

    createTimelineItem(flow, type) {
        const item = document.createElement('div');
        item.className = `timeline-item ${flow.status === 'error' || flow.status === 'timeout' ? 'error' : ''}`;
        item.style.cursor = 'pointer';
        
        const statusClass = flow.status === 'completed' ? '' : 
                           flow.status === 'error' || flow.status === 'timeout' ? 'error' : 'warning';
        
        const duration = this.formatDuration(flow.duration);
        const timeAgo = this.formatTimeAgo(new Date(flow.startTime));
        
        let title, details;
        
        if (type === 'agent') {
            title = `Analysis Request - ${flow.status}`;
            details = `${flow.request.substring(0, 80)}...
Duration: ${duration} | Model: ${flow.model.split('.').pop()}
Tools: ${flow.tools.length} calls | Tokens: ${flow.tokens.input + flow.tokens.output}`;
        } else {
            title = `Monitor Cycle #${flow.cycle} - ${flow.status}`;
            details = `Background monitoring cycle completed
Duration: ${duration} | Model: ${flow.model.split('.').pop()}
Insights: ${flow.insights.anomalies} anomalies, ${flow.insights.warnings} warnings`;
        }

        item.innerHTML = `
            <div class="timeline-dot ${statusClass}"></div>
            <div class="timeline-content">
                <div class="timeline-time">${timeAgo}</div>
                <div class="timeline-title">${title}</div>
                <div class="timeline-details">${details}</div>
            </div>
        `;

        item.addEventListener('click', () => {
            this.showFlowDetails(flow, type);
        });

        return item;
    }

    async showFlowDetails(flow, type) {
        this.selectedFlow = { flow, type };
        const detailsContainer = document.getElementById('detailedFlowInfo');
        if (!detailsContainer) return;

        const duration = this.formatDuration(flow.duration);
        const startTime = new Date(flow.startTime).toLocaleString();
        const endTime = new Date(flow.endTime).toLocaleString();

        let toolsHtml = '';
        if (flow.tools && flow.tools.length > 0) {
            toolsHtml = flow.tools.map(tool => {
                if (tool.command) {
                    return `<li><strong>${tool.name}</strong>: ${tool.command} (${this.formatDuration(tool.duration)})</li>`;
                } else if (tool.commands) {
                    return `<li><strong>${tool.name}</strong>: ${tool.commands} commands (${this.formatDuration(tool.duration)})</li>`;
                } else if (tool.file) {
                    return `<li><strong>${tool.name}</strong>: ${tool.file} (${this.formatDuration(tool.duration)})</li>`;
                }
                return `<li><strong>${tool.name}</strong> (${this.formatDuration(tool.duration)})</li>`;
            }).join('');
        }

        let typeSpecificHtml = '';
        if (type === 'agent') {
            typeSpecificHtml = `
                <div style="margin-bottom: 15px;">
                    <strong>Analysis Request:</strong>
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 5px; font-family: monospace; font-size: 12px;">
                        ${flow.request}
                    </div>
                </div>
                <div style="margin-bottom: 15px;">
                    <strong>Scope:</strong> ${flow.metadata.scope}
                    ${flow.metadata.namespace ? ` | <strong>Namespace:</strong> ${flow.metadata.namespace}` : ''}
                </div>
            `;
        } else {
            typeSpecificHtml = `
                <div style="margin-bottom: 15px;">
                    <strong>Monitor Cycle:</strong> #${flow.cycle}
                </div>
                <div style="margin-bottom: 15px;">
                    <strong>Insights Generated:</strong>
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        <li>Anomalies detected: ${flow.insights.anomalies}</li>
                        <li>Warnings issued: ${flow.insights.warnings}</li>
                        <li>Recommendations: ${flow.insights.recommendations}</li>
                    </ul>
                </div>
            `;
        }

        // Trace information section
        let traceHtml = '';
        if (flow.trace_id) {
            traceHtml = `
                <div style="margin-bottom: 15px;">
                    <strong>🔍 Trace Information:</strong>
                    <div style="background: #e3f2fd; padding: 10px; border-radius: 4px; margin-top: 5px;">
                        <div><strong>Trace ID:</strong> <code>${flow.trace_id}</code></div>
                        ${flow.spans && flow.spans.length > 0 ? `
                            <div style="margin-top: 10px;"><strong>Spans (${flow.spans.length}):</strong></div>
                            <div style="margin-left: 15px; margin-top: 5px;">
                                ${flow.spans.map(span => `
                                    <div style="margin-bottom: 8px; padding: 8px; background: white; border-radius: 3px; border-left: 3px solid ${span.status === 'success' ? '#28a745' : '#dc3545'};">
                                        <div><strong>${span.name}</strong> (${span.status})</div>
                                        ${span.duration ? `<div style="font-size: 12px; color: #6c757d;">Duration: ${this.formatDuration(span.duration)}</div>` : ''}
                                        ${span.metadata && Object.keys(span.metadata).length > 0 ? `
                                            <div style="font-size: 11px; color: #6c757d; margin-top: 3px;">
                                                ${Object.entries(span.metadata).map(([key, value]) => `${key}: ${value}`).join(', ')}
                                            </div>
                                        ` : ''}
                                    </div>
                                `).join('')}
                            </div>
                        ` : '<div style="margin-top: 5px; color: #6c757d; font-size: 12px;">No spans available</div>'}
                        <button onclick="window.flowVisualizer.showTraceDetails('${flow.trace_id}')" 
                                style="margin-top: 10px; padding: 4px 8px; background: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 12px;">
                            View Full Trace
                        </button>
                    </div>
                </div>
            `;
        } else {
            traceHtml = `
                <div style="margin-bottom: 15px;">
                    <strong>🔍 Trace Information:</strong>
                    <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 5px; color: #6c757d; font-size: 12px;">
                        No trace data available for this flow
                    </div>
                </div>
            `;
        }

        detailsContainer.innerHTML = `
            <div style="background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px;">
                <h4 style="margin-bottom: 15px; color: #2c3e50;">
                    ${type === 'agent' ? '🤖 Agent Analysis' : '📡 Background Monitor'} Flow Details
                </h4>
                
                ${typeSpecificHtml}
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">
                    <div>
                        <strong>Status:</strong> 
                        <span style="color: ${flow.status === 'completed' ? '#28a745' : '#dc3545'};">
                            ${flow.status.toUpperCase()}
                        </span>
                    </div>
                    <div><strong>Duration:</strong> ${duration}</div>
                    <div><strong>Start Time:</strong> ${startTime}</div>
                    <div><strong>End Time:</strong> ${endTime}</div>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <strong>Model:</strong> ${flow.model}
                </div>
                
                <div style="margin-bottom: 15px;">
                    <strong>Token Usage:</strong>
                    Input: ${flow.tokens.input.toLocaleString()} | 
                    Output: ${flow.tokens.output.toLocaleString()} | 
                    Total: ${(flow.tokens.input + flow.tokens.output).toLocaleString()}
                </div>
                
                ${toolsHtml ? `
                <div style="margin-bottom: 15px;">
                    <strong>Tool Calls:</strong>
                    <ul style="margin-left: 20px; margin-top: 5px;">
                        ${toolsHtml}
                    </ul>
                </div>
                ` : ''}
                
                ${traceHtml}
                
                <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e9ecef;">
                    <strong>Flow ID:</strong> <code style="background: #f8f9fa; padding: 2px 6px; border-radius: 3px;">${flow.id}</code>
                </div>
            </div>
        `;
    }

    async showTraceDetails(traceId) {
        try {
            const trace = await this.fetchTraceById(traceId);
            if (!trace) {
                alert('Trace not found or could not be loaded');
                return;
            }

            const detailsContainer = document.getElementById('detailedFlowInfo');
            if (!detailsContainer) return;

            const duration = this.formatDuration(trace.duration);
            const startTime = new Date(trace.startTime).toLocaleString();
            const endTime = new Date(trace.endTime).toLocaleString();

            let spansHtml = '';
            if (trace.spans && trace.spans.length > 0) {
                spansHtml = trace.spans.map((span, index) => `
                    <div style="margin-bottom: 15px; padding: 15px; background: ${span.status === 'success' ? '#d4edda' : '#f8d7da'}; border-radius: 6px; border-left: 4px solid ${span.status === 'success' ? '#28a745' : '#dc3545'};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <h5 style="margin: 0; color: #2c3e50;">Span ${index + 1}: ${span.name}</h5>
                            <span style="padding: 2px 8px; background: ${span.status === 'success' ? '#28a745' : '#dc3545'}; color: white; border-radius: 12px; font-size: 11px;">
                                ${span.status.toUpperCase()}
                            </span>
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; font-size: 13px;">
                            <div><strong>Span ID:</strong> <code>${span.span_id}</code></div>
                            <div><strong>Duration:</strong> ${span.duration ? this.formatDuration(span.duration) : 'N/A'}</div>
                            ${span.start_time ? `<div><strong>Start:</strong> ${new Date(span.start_time).toLocaleTimeString()}</div>` : ''}
                            ${span.end_time ? `<div><strong>End:</strong> ${new Date(span.end_time).toLocaleTimeString()}</div>` : ''}
                        </div>
                        
                        ${span.metadata && Object.keys(span.metadata).length > 0 ? `
                            <div style="margin-top: 10px;">
                                <strong>Metadata:</strong>
                                <div style="background: rgba(255,255,255,0.7); padding: 8px; border-radius: 4px; margin-top: 5px; font-family: monospace; font-size: 11px;">
                                    ${Object.entries(span.metadata).map(([key, value]) => `<div><strong>${key}:</strong> ${JSON.stringify(value)}</div>`).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `).join('');
            } else {
                spansHtml = '<div style="color: #6c757d; text-align: center; padding: 20px;">No spans available for this trace</div>';
            }

            detailsContainer.innerHTML = `
                <div style="background: white; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px;">
                    <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 20px;">
                        <h4 style="margin: 0; color: #2c3e50;">🔍 Trace Details</h4>
                        <button onclick="window.flowVisualizer.showFlowDetails(window.flowVisualizer.selectedFlow.flow, window.flowVisualizer.selectedFlow.type)" 
                                style="padding: 6px 12px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px;">
                            ← Back to Flow
                        </button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px;">
                        <div><strong>Trace ID:</strong> <code>${trace.trace_id}</code></div>
                        <div><strong>Flow ID:</strong> <code>${trace.flow_id}</code></div>
                        <div><strong>Type:</strong> ${trace.type}</div>
                        <div><strong>Status:</strong> <span style="color: ${trace.status === 'success' ? '#28a745' : '#dc3545'};">${trace.status.toUpperCase()}</span></div>
                        <div><strong>Duration:</strong> ${duration}</div>
                        <div><strong>Spans:</strong> ${trace.spans ? trace.spans.length : 0}</div>
                        <div><strong>Start Time:</strong> ${startTime}</div>
                        <div><strong>End Time:</strong> ${endTime}</div>
                    </div>
                    
                    ${trace.metadata && Object.keys(trace.metadata).length > 0 ? `
                        <div style="margin-bottom: 20px;">
                            <strong>Trace Metadata:</strong>
                            <div style="background: #e3f2fd; padding: 10px; border-radius: 4px; margin-top: 5px; font-family: monospace; font-size: 12px;">
                                ${Object.entries(trace.metadata).map(([key, value]) => `<div><strong>${key}:</strong> ${JSON.stringify(value)}</div>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    <div>
                        <h5 style="margin-bottom: 15px; color: #2c3e50;">Execution Spans</h5>
                        ${spansHtml}
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Failed to show trace details:', error);
            alert('Failed to load trace details');
        }
    }

    updateMetrics() {
        const totalFlows = this.flows.agent.length + this.flows.monitor.length;
        const activeAgents = 2; // Agent + Monitor
        
        // Calculate average duration
        const allFlows = [...this.flows.agent, ...this.flows.monitor];
        const avgDuration = allFlows.length > 0 ? 
            allFlows.reduce((sum, flow) => sum + flow.duration, 0) / allFlows.length : 0;
        
        // Calculate success rate
        const successfulFlows = allFlows.filter(flow => flow.status === 'completed').length;
        const successRate = allFlows.length > 0 ? (successfulFlows / allFlows.length) * 100 : 0;

        // Update metric displays
        this.updateMetricValue('totalFlows', totalFlows);
        this.updateMetricValue('activeAgents', activeAgents);
        this.updateMetricValue('avgDuration', this.formatDuration(avgDuration));
        this.updateMetricValue('successRate', `${successRate.toFixed(1)}%`);
        this.updateMetricValue('totalTraces', this.traces.length);
    }

    updateMetricValue(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    updateStatus(status) {
        const statusElement = document.getElementById('flowStatus');
        const agentStatusElement = document.getElementById('agentFlowStatus');
        const monitorStatusElement = document.getElementById('monitorFlowStatus');

        if (statusElement) {
            statusElement.className = `status-indicator ${status}`;
            
            switch (status) {
                case 'loading':
                    statusElement.innerHTML = '<span class="loading-spinner" style="width: 12px; height: 12px;"></span> Loading...';
                    break;
                case 'active':
                    statusElement.innerHTML = '🟢 Active';
                    break;
                case 'error':
                    statusElement.innerHTML = '🔴 Error';
                    break;
            }
        }

        if (agentStatusElement) {
            agentStatusElement.className = `status-indicator ${status === 'active' ? 'processing' : status}`;
            agentStatusElement.innerHTML = status === 'active' ? 
                '<span class="loading-spinner" style="width: 12px; height: 12px;"></span> Monitoring...' :
                status === 'error' ? '🔴 Error' : '⏸️ Inactive';
        }

        if (monitorStatusElement) {
            monitorStatusElement.className = `status-indicator ${status === 'active' ? 'processing' : status}`;
            monitorStatusElement.innerHTML = status === 'active' ? 
                '<span class="loading-spinner" style="width: 12px; height: 12px;"></span> Monitoring...' :
                status === 'error' ? '🔴 Error' : '⏸️ Inactive';
        }
    }

    toggleAutoRefresh(enabled = null) {
        if (enabled !== null) {
            this.autoRefreshEnabled = enabled;
        } else {
            this.autoRefreshEnabled = !this.autoRefreshEnabled;
        }

        if (this.autoRefreshEnabled) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    updateRefreshInterval(interval) {
        this.refreshInterval = interval;
        if (this.autoRefreshEnabled) {
            this.stopAutoRefresh();
            this.startAutoRefresh();
        }
    }

    startAutoRefresh() {
        this.stopAutoRefresh();
        if (this.autoRefreshEnabled) {
            this.refreshTimer = setInterval(() => {
                this.refreshFlows();
            }, this.refreshInterval);
        }
    }

    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    clearFlows() {
        this.flows = { agent: [], monitor: [] };
        this.updateTimelines();
        this.updateMetrics();
        
        const detailsContainer = document.getElementById('detailedFlowInfo');
        if (detailsContainer) {
            detailsContainer.innerHTML = '<p style="color: #6c757d; text-align: center; margin-top: 50px;">Click on any flow item above to see detailed information here.</p>';
        }
    }

    exportFlowData() {
        const data = {
            timestamp: new Date().toISOString(),
            flows: this.flows,
            metrics: {
                totalFlows: this.flows.agent.length + this.flows.monitor.length,
                activeAgents: 2,
                exportedAt: new Date().toISOString()
            }
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `kubeintel-flows-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    formatDuration(ms) {
        if (ms < 1000) return `${ms}ms`;
        if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
        return `${(ms / 60000).toFixed(1)}m`;
    }

    formatTimeAgo(date) {
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return `${Math.floor(diff / 86400000)}d ago`;
    }
}

// Global functions for HTML onclick handlers
function refreshFlows() {
    if (window.flowVisualizer) {
        window.flowVisualizer.refreshFlows();
    }
}

function clearFlows() {
    if (window.flowVisualizer) {
        window.flowVisualizer.clearFlows();
    }
}

function toggleAutoRefresh() {
    if (window.flowVisualizer) {
        const checkbox = document.getElementById('autoRefresh');
        window.flowVisualizer.toggleAutoRefresh(checkbox.checked);
    }
}

function updateRefreshInterval() {
    if (window.flowVisualizer) {
        const select = document.getElementById('refreshInterval');
        window.flowVisualizer.updateRefreshInterval(parseInt(select.value));
    }
}

function switchViewMode() {
    if (window.flowVisualizer) {
        window.flowVisualizer.switchViewMode();
    }
}

function filterTraces() {
    if (window.flowVisualizer) {
        const select = document.getElementById('traceTypeFilter');
        window.flowVisualizer.filterTraces(select.value);
    }
}

function exportFlowData() {
    if (window.flowVisualizer) {
        window.flowVisualizer.exportFlowData();
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize when DOM is loaded
    window.flowVisualizer = new FlowVisualizer();
});
