#!/usr/bin/env python3
"""
Hybrid Test Report Merger
Combines JMeter and Selenium test results into a unified HTML report
"""

import os
import json
import csv
import sys
from datetime import datetime
from pathlib import Path
import argparse

class HybridReportMerger:
    def __init__(self, base_path="../reports"):
        self.base_path = Path(base_path)
        self.jmeter_report_path = self.base_path / "jmeter-report"
        self.selenium_report_path = self.base_path / "selenium-report"
        self.output_path = self.base_path / "merged-report.html"
        
    def parse_jmeter_results(self):
        """Parse JMeter JTL results file"""
        jtl_file = self.jmeter_report_path / "results.jtl"
        jmeter_data = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_response_time': 0,
            'min_response_time': float('inf'),
            'max_response_time': 0,
            'throughput': 0,
            'error_rate': 0,
            'requests': []
        }
        
        if not jtl_file.exists():
            print(f"Warning: JMeter results file not found: {jtl_file}")
            return jmeter_data
            
        try:
            with open(jtl_file, 'r') as f:
                reader = csv.DictReader(f)
                response_times = []
                
                for row in reader:
                    jmeter_data['total_requests'] += 1
                    
                    # Parse response time
                    response_time = int(row.get('elapsed', 0))
                    response_times.append(response_time)
                    
                    # Update min/max
                    jmeter_data['min_response_time'] = min(jmeter_data['min_response_time'], response_time)
                    jmeter_data['max_response_time'] = max(jmeter_data['max_response_time'], response_time)
                    
                    # Check success
                    success = row.get('success', 'false').lower() == 'true'
                    if success:
                        jmeter_data['successful_requests'] += 1
                    else:
                        jmeter_data['failed_requests'] += 1
                    
                    # Store request details
                    jmeter_data['requests'].append({
                        'timestamp': row.get('timeStamp', ''),
                        'label': row.get('label', ''),
                        'response_time': response_time,
                        'success': success,
                        'response_code': row.get('responseCode', ''),
                        'message': row.get('responseMessage', '')
                    })
                
                # Calculate averages and rates
                if response_times:
                    jmeter_data['avg_response_time'] = sum(response_times) / len(response_times)
                    jmeter_data['error_rate'] = (jmeter_data['failed_requests'] / jmeter_data['total_requests']) * 100
                    
                    # Calculate throughput (requests per second)
                    if jmeter_data['requests']:
                        start_time = int(jmeter_data['requests'][0]['timestamp'])
                        end_time = int(jmeter_data['requests'][-1]['timestamp'])
                        duration = (end_time - start_time) / 1000  # Convert to seconds
                        if duration > 0:
                            jmeter_data['throughput'] = jmeter_data['total_requests'] / duration
                
        except Exception as e:
            print(f"Error parsing JMeter results: {e}")
            
        return jmeter_data
    
    def parse_selenium_results(self):
        """Parse Selenium performance log"""
        log_file = self.selenium_report_path / "selenium_performance.log"
        json_file = self.selenium_report_path / "selenium_performance.json"
        
        selenium_data = {
            'total_tests': 0,
            'successful_tests': 0,
            'failed_tests': 0,
            'avg_response_time': 0,
            'min_response_time': float('inf'),
            'max_response_time': 0,
            'tests': []
        }
        
        # Try to parse JSON file first, then fall back to CSV
        if json_file.exists():
            try:
                with open(json_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            test_data = json.loads(line.strip())
                            selenium_data['total_tests'] += 1
                            
                            response_time = test_data.get('responseTime', 0)
                            selenium_data['min_response_time'] = min(selenium_data['min_response_time'], response_time)
                            selenium_data['max_response_time'] = max(selenium_data['max_response_time'], response_time)
                            
                            if test_data.get('success', False):
                                selenium_data['successful_tests'] += 1
                            else:
                                selenium_data['failed_tests'] += 1
                            
                            selenium_data['tests'].append(test_data)
                            
            except Exception as e:
                print(f"Error parsing Selenium JSON results: {e}")
        
        elif log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    reader = csv.DictReader(f)
                    response_times = []
                    
                    for row in reader:
                        selenium_data['total_tests'] += 1
                        
                        response_time = int(row.get('responseTime', 0))
                        response_times.append(response_time)
                        
                        selenium_data['min_response_time'] = min(selenium_data['min_response_time'], response_time)
                        selenium_data['max_response_time'] = max(selenium_data['max_response_time'], response_time)
                        
                        success = row.get('success', 'false').lower() == 'true'
                        if success:
                            selenium_data['successful_tests'] += 1
                        else:
                            selenium_data['failed_tests'] += 1
                        
                        selenium_data['tests'].append({
                            'timestamp': row.get('timestamp', ''),
                            'test': row.get('testName', ''),
                            'responseTime': response_time,
                            'success': success,
                            'message': row.get('message', '')
                        })
                    
                    if response_times:
                        selenium_data['avg_response_time'] = sum(response_times) / len(response_times)
                        
            except Exception as e:
                print(f"Error parsing Selenium log results: {e}")
        else:
            print(f"Warning: Selenium results files not found: {log_file} or {json_file}")
            
        return selenium_data
    
    def generate_html_report(self, jmeter_data, selenium_data):
        """Generate unified HTML report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Hybrid Test Report - {timestamp}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .success {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .danger {{ color: #dc3545; }}
        .info {{ color: #17a2b8; }}
        .section {{
            margin: 30px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .metric {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }}
        .metric-label {{
            font-weight: bold;
            color: #666;
            font-size: 0.9em;
        }}
        .metric-value {{
            font-size: 1.5em;
            color: #333;
            margin: 5px 0;
        }}
        .test-results {{
            margin: 20px 0;
        }}
        .test-item {{
            background: #f8f9fa;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #28a745;
        }}
        .test-item.failed {{
            border-left-color: #dc3545;
        }}
        .test-name {{
            font-weight: bold;
            color: #333;
        }}
        .test-details {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        .footer {{
            background: #333;
            color: white;
            text-align: center;
            padding: 20px;
        }}
        .chart-container {{
            margin: 20px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Hybrid Test Report</h1>
            <p>JMeter Load Testing + Selenium UI Testing</p>
            <p>Generated on: {timestamp}</p>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <h3>📊 Total Tests</h3>
                <div class="value info">{jmeter_data['total_requests'] + selenium_data['total_tests']}</div>
                <p>JMeter: {jmeter_data['total_requests']} | Selenium: {selenium_data['total_tests']}</p>
            </div>
            <div class="summary-card">
                <h3>✅ Success Rate</h3>
                <div class="value success">{self._calculate_overall_success_rate(jmeter_data, selenium_data):.1f}%</div>
                <p>Overall test success rate</p>
            </div>
            <div class="summary-card">
                <h3>⚡ Avg Response Time</h3>
                <div class="value info">{self._calculate_avg_response_time(jmeter_data, selenium_data):.0f}ms</div>
                <p>Combined average response time</p>
            </div>
            <div class="summary-card">
                <h3>🔥 Throughput</h3>
                <div class="value warning">{jmeter_data['throughput']:.1f} req/s</div>
                <p>JMeter requests per second</p>
            </div>
        </div>
        
        <div class="section">
            <h2>📈 JMeter Load Test Results</h2>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">Total Requests</div>
                    <div class="metric-value">{jmeter_data['total_requests']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Successful Requests</div>
                    <div class="metric-value success">{jmeter_data['successful_requests']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Failed Requests</div>
                    <div class="metric-value danger">{jmeter_data['failed_requests']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Error Rate</div>
                    <div class="metric-value {'danger' if jmeter_data['error_rate'] > 5 else 'success'}">{jmeter_data['error_rate']:.2f}%</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Average Response Time</div>
                    <div class="metric-value info">{jmeter_data['avg_response_time']:.0f}ms</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Min Response Time</div>
                    <div class="metric-value info">{jmeter_data['min_response_time'] if jmeter_data['min_response_time'] != float('inf') else 0}ms</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Max Response Time</div>
                    <div class="metric-value info">{jmeter_data['max_response_time']}ms</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Throughput</div>
                    <div class="metric-value warning">{jmeter_data['throughput']:.2f} req/s</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🖥️ Selenium UI Test Results</h2>
            <div class="metrics-grid">
                <div class="metric">
                    <div class="metric-label">Total Tests</div>
                    <div class="metric-value">{selenium_data['total_tests']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Successful Tests</div>
                    <div class="metric-value success">{selenium_data['successful_tests']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Failed Tests</div>
                    <div class="metric-value danger">{selenium_data['failed_tests']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Average Response Time</div>
                    <div class="metric-value info">{selenium_data['avg_response_time']:.0f}ms</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Min Response Time</div>
                    <div class="metric-value info">{selenium_data['min_response_time'] if selenium_data['min_response_time'] != float('inf') else 0}ms</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Max Response Time</div>
                    <div class="metric-value info">{selenium_data['max_response_time']}ms</div>
                </div>
            </div>
            
            <div class="test-results">
                <h3>Test Details</h3>
                {self._generate_test_details_html(selenium_data['tests'])}
            </div>
        </div>
        
        <div class="section">
            <h2>📋 Recommendations</h2>
            <div class="recommendations">
                {self._generate_recommendations(jmeter_data, selenium_data)}
            </div>
        </div>
        
        <div class="footer">
            <p>Hybrid Test Framework | Generated by merge_reports.py</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html_content
    
    def _calculate_overall_success_rate(self, jmeter_data, selenium_data):
        """Calculate overall success rate"""
        total_tests = jmeter_data['total_requests'] + selenium_data['total_tests']
        if total_tests == 0:
            return 0
        successful_tests = jmeter_data['successful_requests'] + selenium_data['successful_tests']
        return (successful_tests / total_tests) * 100
    
    def _calculate_avg_response_time(self, jmeter_data, selenium_data):
        """Calculate combined average response time"""
        total_requests = jmeter_data['total_requests'] + selenium_data['total_tests']
        if total_requests == 0:
            return 0
        
        jmeter_total_time = jmeter_data['avg_response_time'] * jmeter_data['total_requests']
        selenium_total_time = selenium_data['avg_response_time'] * selenium_data['total_tests']
        
        return (jmeter_total_time + selenium_total_time) / total_requests
    
    def _generate_test_details_html(self, tests):
        """Generate HTML for test details"""
        if not tests:
            return "<p>No test details available.</p>"
        
        html = ""
        for test in tests:
            status_class = "failed" if not test.get('success', False) else ""
            html += f"""
            <div class="test-item {status_class}">
                <div class="test-name">{test.get('test', 'Unknown Test')}</div>
                <div class="test-details">
                    Response Time: {test.get('responseTime', 0)}ms | 
                    Status: {'✅ Passed' if test.get('success', False) else '❌ Failed'} | 
                    Message: {test.get('message', 'N/A')}
                </div>
            </div>
            """
        return html
    
    def _generate_recommendations(self, jmeter_data, selenium_data):
        """Generate recommendations based on test results"""
        recommendations = []
        
        # JMeter recommendations
        if jmeter_data['error_rate'] > 5:
            recommendations.append("🔴 High error rate detected in load tests. Consider reducing load or optimizing backend.")
        
        if jmeter_data['avg_response_time'] > 2000:
            recommendations.append("🟡 High average response time in load tests. Consider performance optimization.")
        
        if jmeter_data['throughput'] < 10:
            recommendations.append("🟡 Low throughput detected. Check server capacity and network conditions.")
        
        # Selenium recommendations
        if selenium_data['failed_tests'] > 0:
            recommendations.append("🔴 Some UI tests failed. Review test results and fix issues.")
        
        if selenium_data['avg_response_time'] > 3000:
            recommendations.append("🟡 High UI response times. Consider frontend optimization.")
        
        # General recommendations
        if not recommendations:
            recommendations.append("✅ All tests passed successfully! System performance looks good.")
        
        html = "<ul>"
        for rec in recommendations:
            html += f"<li>{rec}</li>"
        html += "</ul>"
        
        return html
    
    def merge_reports(self):
        """Main method to merge reports"""
        print("🔄 Parsing JMeter results...")
        jmeter_data = self.parse_jmeter_results()
        
        print("🔄 Parsing Selenium results...")
        selenium_data = self.parse_selenium_results()
        
        print("🔄 Generating merged HTML report...")
        html_content = self.generate_html_report(jmeter_data, selenium_data)
        
        # Write HTML report
        with open(self.output_path, 'w') as f:
            f.write(html_content)
        
        print(f"✅ Merged report generated: {self.output_path}")
        
        # Also generate JSON summary
        json_path = self.base_path / "merged-report.json"
        summary_data = {
            'timestamp': datetime.now().isoformat(),
            'jmeter': jmeter_data,
            'selenium': selenium_data,
            'summary': {
                'total_tests': jmeter_data['total_requests'] + selenium_data['total_tests'],
                'success_rate': self._calculate_overall_success_rate(jmeter_data, selenium_data),
                'avg_response_time': self._calculate_avg_response_time(jmeter_data, selenium_data)
            }
        }
        
        with open(json_path, 'w') as f:
            json.dump(summary_data, f, indent=2)
        
        print(f"✅ JSON summary generated: {json_path}")

def main():
    parser = argparse.ArgumentParser(description='Merge JMeter and Selenium test reports')
    parser.add_argument('--reports-path', default='../reports', 
                       help='Path to reports directory (default: ../reports)')
    
    args = parser.parse_args()
    
    merger = HybridReportMerger(args.reports_path)
    merger.merge_reports()

if __name__ == "__main__":
    main()
