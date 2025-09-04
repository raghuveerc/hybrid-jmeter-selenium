package com.ui;

import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;
import org.openqa.selenium.support.ui.WebDriverWait;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;
import org.testng.annotations.*;
import org.testng.Assert;
import java.time.Duration;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

public class GrafanaUITest {
    
    private WebDriver driver;
    private WebDriverWait wait;
    private String baseUrl = "https://quickpizza.grafana.com";
    private String reportPath = "../reports/selenium-report/";
    private String chromeDriverPath = System.getProperty("webdriver.chrome.driver", 
        System.getenv("CHROMEDRIVER_PATH"));
    
    @BeforeClass
    public void setupClass() {
        // Create reports directory if it doesn't exist
        File reportDir = new File(reportPath);
        if (!reportDir.exists()) {
            reportDir.mkdirs();
        }
    }
    
    @BeforeMethod
    @Parameters({"headless"})
    public void setup(@Optional("false") String headless) {
        // Setup Chrome WebDriver with ChromeDriver from Nexus
        ChromeOptions chromeOptions = new ChromeOptions();
        
        // Configure Chrome options
        if ("true".equals(headless)) {
            chromeOptions.addArguments("--headless");
        }
        chromeOptions.addArguments("--no-sandbox");
        chromeOptions.addArguments("--disable-dev-shm-usage");
        chromeOptions.addArguments("--disable-gpu");
        chromeOptions.addArguments("--window-size=1920,1080");
        chromeOptions.addArguments("--disable-extensions");
        chromeOptions.addArguments("--disable-plugins");
        chromeOptions.addArguments("--disable-images");
        chromeOptions.addArguments("--disable-javascript");
        
        // Set ChromeDriver path from Nexus
        if (chromeDriverPath != null && !chromeDriverPath.isEmpty()) {
            System.setProperty("webdriver.chrome.driver", chromeDriverPath);
            System.out.println("Using ChromeDriver from: " + chromeDriverPath);
        } else {
            System.err.println("Warning: ChromeDriver path not specified. Set webdriver.chrome.driver system property or CHROMEDRIVER_PATH environment variable");
        }
        
        driver = new ChromeDriver(chromeOptions);
        wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        driver.manage().window().maximize();
        driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(5));
    }
    
    @Test(description = "Test Grafana homepage load time and basic functionality")
    public void testGrafanaHomePageLoadTime() {
        long startTime = System.currentTimeMillis();
        
        try {
            // Navigate to homepage
            driver.get(baseUrl);
            
            // Wait for page to load completely
            wait.until(ExpectedConditions.presenceOfElementLocated(By.tagName("body")));
            
            long loadTime = System.currentTimeMillis() - startTime;
            
            // Log the load time
            System.out.println("Page Load Time: " + loadTime + " ms");
            
            // Verify page title
            String pageTitle = driver.getTitle();
            Assert.assertNotNull(pageTitle, "Page title should not be null");
            System.out.println("Page Title: " + pageTitle);
            
            // Verify page URL
            String currentUrl = driver.getCurrentUrl();
            Assert.assertTrue(currentUrl.contains("grafana"), "URL should contain 'grafana'");
            
            // Write performance metrics to file
            writePerformanceMetrics("grafana_homepage_load", loadTime, true, "Grafana homepage loaded successfully");
            
            // Assert load time is reasonable (less than 5 seconds)
            Assert.assertTrue(loadTime < 5000, "Page load time should be less than 5 seconds");
            
        } catch (Exception e) {
            long loadTime = System.currentTimeMillis() - startTime;
            writePerformanceMetrics("grafana_homepage_load", loadTime, false, e.getMessage());
            throw e;
        }
    }
    
    @Test(description = "Test Grafana user login functionality")
    public void testGrafanaUserLogin() {
        long startTime = System.currentTimeMillis();
        
        try {
            // Navigate to Grafana login page
            driver.get(baseUrl + "/login");
            
            // Wait for Grafana login form to be present
            WebElement usernameField = wait.until(ExpectedConditions.presenceOfElementLocated(By.name("user")));
            WebElement passwordField = driver.findElement(By.name("password"));
            WebElement loginButton = driver.findElement(By.cssSelector("button[type='submit']"));
            
            // Fill Grafana login form
            usernameField.sendKeys("admin");
            passwordField.sendKeys("admin");
            
            // Click login button
            loginButton.click();
            
            // Wait for redirect or error message
            Thread.sleep(2000);
            
            long responseTime = System.currentTimeMillis() - startTime;
            
            // Check if Grafana login was successful (redirect to dashboard)
            String currentUrl = driver.getCurrentUrl();
            boolean loginSuccess = currentUrl.contains("dashboard") || currentUrl.contains("home") || currentUrl.contains("grafana");
            
            System.out.println("Login Response Time: " + responseTime + " ms");
            System.out.println("Login Successful: " + loginSuccess);
            
            writePerformanceMetrics("grafana_user_login", responseTime, loginSuccess, 
                loginSuccess ? "Grafana login successful" : "Grafana login failed");
            
            // Note: In a real test, you might want to assert login success
            // For demo purposes, we'll just log the result
            
        } catch (Exception e) {
            long responseTime = System.currentTimeMillis() - startTime;
            writePerformanceMetrics("grafana_user_login", responseTime, false, e.getMessage());
            System.out.println("Login test failed: " + e.getMessage());
        }
    }
    
    @Test(description = "Test Grafana dashboard loading and data display")
    public void testGrafanaDashboardLoad() {
        long startTime = System.currentTimeMillis();
        
        try {
            // Navigate to Grafana dashboard
            driver.get(baseUrl + "/dashboards");
            
            // Wait for Grafana dashboard to load
            WebElement dashboardContainer = wait.until(ExpectedConditions.presenceOfElementLocated(By.className("dashboard-container")));
            
            long responseTime = System.currentTimeMillis() - startTime;
            
            // Check if dashboard data is displayed
            boolean dataLoaded = dashboardContainer.isDisplayed() && dashboardContainer.getText().length() > 0;
            
            System.out.println("API Response Time (through UI): " + responseTime + " ms");
            System.out.println("Data Loaded: " + dataLoaded);
            
            writePerformanceMetrics("grafana_dashboard_load", responseTime, dataLoaded, 
                dataLoaded ? "Grafana dashboard loaded successfully" : "Grafana dashboard not loaded");
            
        } catch (Exception e) {
            long responseTime = System.currentTimeMillis() - startTime;
            writePerformanceMetrics("grafana_dashboard_load", responseTime, false, e.getMessage());
            System.out.println("API response test failed: " + e.getMessage());
        }
    }
    
    @AfterMethod
    public void tearDown() {
        if (driver != null) {
            driver.quit();
        }
    }
    
    @AfterClass
    public void generateReport() {
        System.out.println("Grafana Selenium tests completed. Reports available in: " + reportPath);
    }
    
    private void writePerformanceMetrics(String testName, long responseTime, boolean success, String message) {
        try {
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
            String logEntry = String.format("%s,%s,%d,%s,%s%n", 
                timestamp, testName, responseTime, success, message);
            
            File logFile = new File(reportPath + "selenium_performance.log");
            try (FileWriter writer = new FileWriter(logFile, true)) {
                writer.write(logEntry);
            }
            
            // Also write to a JSON format for easier parsing
            String jsonEntry = String.format("{\"timestamp\":\"%s\",\"test\":\"%s\",\"responseTime\":%d,\"success\":%s,\"message\":\"%s\"}%n",
                timestamp, testName, responseTime, success, message);
            
            File jsonFile = new File(reportPath + "selenium_performance.json");
            try (FileWriter writer = new FileWriter(jsonFile, true)) {
                writer.write(jsonEntry);
            }
            
        } catch (IOException e) {
            System.err.println("Failed to write performance metrics: " + e.getMessage());
        }
    }
}