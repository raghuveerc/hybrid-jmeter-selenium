#!/bin/bash

# Hybrid JMeter + Selenium Test Orchestrator
# This script coordinates load testing with JMeter and UI testing with Selenium

set -e  # Exit on any error

# Configuration
JMETER_TEST_PLAN="../jmeter-tests/frontier_load_test.jmx"
JMETER_RESULTS="../reports/jmeter-report/results.jtl"
JMETER_HTML_REPORT="../reports/jmeter-report/"
SELENIUM_PROJECT="../selenium-tests"
SELENIUM_REPORT="../reports/selenium-report/"
MERGED_REPORT="../reports/merged-report.html"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check JMeter
    if ! command_exists jmeter; then
        print_error "JMeter is not installed or not in PATH"
        print_status "Please install JMeter and ensure it's in your PATH"
        exit 1
    fi
    
    # Check Java
    if ! command_exists java; then
        print_error "Java is not installed or not in PATH"
        exit 1
    fi
    
    # Check Maven
    if ! command_exists mvn; then
        print_error "Maven is not installed or not in PATH"
        exit 1
    fi
    
    # Check if JMeter test plan exists
    if [ ! -f "$JMETER_TEST_PLAN" ]; then
        print_error "JMeter test plan not found: $JMETER_TEST_PLAN"
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Function to create report directories
setup_directories() {
    print_status "Setting up report directories..."
    
    mkdir -p "$(dirname "$JMETER_RESULTS")"
    mkdir -p "$JMETER_HTML_REPORT"
    mkdir -p "$SELENIUM_REPORT"
    mkdir -p "$(dirname "$MERGED_REPORT")"
    
    print_success "Report directories created"
}

# Function to run JMeter load test
run_jmeter_test() {
    print_status "Starting JMeter load test..."
    print_status "Test Plan: $JMETER_TEST_PLAN"
    print_status "Results: $JMETER_RESULTS"
    print_status "HTML Report: $JMETER_HTML_REPORT"
    
    # Run JMeter in non-GUI mode
    jmeter -n -t "$JMETER_TEST_PLAN" \
           -l "$JMETER_RESULTS" \
           -e -o "$JMETER_HTML_REPORT" \
           -Jjmeter.save.saveservice.response_data=false \
           -Jjmeter.save.saveservice.samplerData=false \
           -Jjmeter.save.saveservice.requestHeaders=false \
           -Jjmeter.save.saveservice.responseHeaders=false &
    
    JMETER_PID=$!
    print_success "JMeter started with PID: $JMETER_PID"
    
    # Wait for JMeter ramp-up period
    print_status "Waiting for JMeter ramp-up (30 seconds)..."
    sleep 30
}

# Function to run Selenium tests
run_selenium_tests() {
    print_status "Starting Selenium UI tests..."
    
    cd "$SELENIUM_PROJECT" || exit 1
    
    # Check if Maven dependencies are installed
    if [ ! -d "target" ]; then
        print_status "Installing Maven dependencies..."
        mvn clean compile test-compile
    fi
    
    # Run Selenium tests
    print_status "Running Selenium tests..."
    mvn test -Dtest=FrontierUITest \
             -Dbrowser=chrome \
             -Dheadless=false \
             -Dmaven.test.failure.ignore=true
    
    cd - > /dev/null
    print_success "Selenium tests completed"
}

# Function to wait for JMeter completion
wait_for_jmeter() {
    print_status "Waiting for JMeter test to complete..."
    
    if [ -n "$JMETER_PID" ]; then
        wait "$JMETER_PID"
        print_success "JMeter test completed"
    else
        print_warning "JMeter PID not found, assuming test completed"
    fi
}

# Function to generate merged report
generate_merged_report() {
    print_status "Generating merged report..."
    
    # Check if Python script exists
    if [ -f "../orchestrator/merge_reports.py" ]; then
        python3 ../orchestrator/merge_reports.py
        print_success "Merged report generated: $MERGED_REPORT"
    else
        print_warning "Merge reports script not found, skipping merged report generation"
    fi
}

# Function to display test summary
display_summary() {
    print_status "Test Execution Summary"
    echo "=================================="
    
    # JMeter results
    if [ -f "$JMETER_RESULTS" ]; then
        print_success "JMeter Results: $JMETER_RESULTS"
        print_success "JMeter HTML Report: $JMETER_HTML_REPORT/index.html"
    else
        print_error "JMeter results not found"
    fi
    
    # Selenium results
    if [ -d "$SELENIUM_REPORT" ]; then
        print_success "Selenium Reports: $SELENIUM_REPORT"
        if [ -f "$SELENIUM_REPORT/selenium_performance.log" ]; then
            print_success "Selenium Performance Log: $SELENIUM_REPORT/selenium_performance.log"
        fi
    else
        print_error "Selenium reports not found"
    fi
    
    # Merged report
    if [ -f "$MERGED_REPORT" ]; then
        print_success "Merged Report: $MERGED_REPORT"
    fi
    
    echo "=================================="
    print_success "Hybrid test execution completed!"
}

# Function to cleanup on exit
cleanup() {
    print_status "Cleaning up..."
    
    # Kill JMeter if still running
    if [ -n "$JMETER_PID" ] && kill -0 "$JMETER_PID" 2>/dev/null; then
        print_status "Stopping JMeter process..."
        kill "$JMETER_PID"
        wait "$JMETER_PID" 2>/dev/null || true
    fi
    
    # Kill any remaining Chrome processes (from Selenium)
    pkill -f "chromedriver" 2>/dev/null || true
    pkill -f "chrome.*--test-type" 2>/dev/null || true
}

# Set up signal handlers for cleanup
trap cleanup EXIT INT TERM

# Main execution
main() {
    echo "=================================="
    echo "  Hybrid JMeter + Selenium Test"
    echo "=================================="
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --jmeter-only)
                JMETER_ONLY=true
                shift
                ;;
            --selenium-only)
                SELENIUM_ONLY=true
                shift
                ;;
            --headless)
                HEADLESS=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --jmeter-only    Run only JMeter tests"
                echo "  --selenium-only  Run only Selenium tests"
                echo "  --headless       Run Selenium tests in headless mode"
                echo "  --help           Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Setup directories
    setup_directories
    
    # Run tests based on options
    if [ "$SELENIUM_ONLY" = true ]; then
        print_status "Running Selenium tests only..."
        run_selenium_tests
    elif [ "$JMETER_ONLY" = true ]; then
        print_status "Running JMeter tests only..."
        run_jmeter_test
        wait_for_jmeter
    else
        print_status "Running hybrid test (JMeter + Selenium)..."
        
        # Start JMeter in background
        run_jmeter_test
        
        # Run Selenium tests while JMeter is running
        run_selenium_tests
        
        # Wait for JMeter to complete
        wait_for_jmeter
    fi
    
    # Generate merged report
    generate_merged_report
    
    # Display summary
    display_summary
}

# Run main function
main "$@"
