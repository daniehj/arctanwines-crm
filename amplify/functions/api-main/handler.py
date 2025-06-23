import json
import os
import time
import socket
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import boto3

# Initialize FastAPI app
app = FastAPI(title="Arctan Wines CRM API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS clients
ssm_client = boto3.client('ssm')
secrets_client = boto3.client('secretsmanager')

def get_environment():
    """Determine environment"""
    amplify_env = os.environ.get('AMPLIFY_ENV', '')
    aws_branch = os.environ.get('AWS_BRANCH', '')
    function_name = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', '')
    
    # Debug info
    env_info = {
        'amplify_env': amplify_env,
        'aws_branch': aws_branch,
        'function_name': function_name
    }
    
    if ('sandbox' in amplify_env.lower() or 
        aws_branch in ['dev', 'test', 'sandbox'] or 
        'sandbox' in function_name.lower() or 
        'test' in function_name.lower()):
        return 'test', env_info
    return 'prod', env_info

@app.get("/")
def root():
    """Root endpoint"""
    return {"message": "Arctan Wines CRM API", "status": "online", "timestamp": time.time()}

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": get_environment(),
        "version": "1.0.0"
    }

@app.get("/config-debug")
def config_debug():
    """Debug configuration and environment"""
    env, env_info = get_environment()
    
    return {
        "environment": env,
        "env_info": env_info,
        "aws_region": os.environ.get('AWS_REGION', 'not-set'),
        "function_name": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'not-set'),
        "timestamp": time.time()
    }

@app.get("/vpc-info")
def vpc_info():
    """Get VPC and network information"""
    try:
        # Try to get metadata about the Lambda environment
        import urllib.request
        import urllib.error
        
        # This will work if Lambda has internet access
        try:
            # Get AWS metadata
            req = urllib.request.Request('http://169.254.169.254/latest/meta-data/instance-id')
            req.add_header('User-Agent', 'lambda-vpc-info')
            with urllib.request.urlopen(req, timeout=5) as response:
                instance_id = response.read().decode()
        except:
            instance_id = "not-available-in-lambda"
            
        # Get network interface info if available
        try:
            import netifaces
            interfaces = netifaces.interfaces()
            interface_info = {}
            for iface in interfaces:
                addrs = netifaces.ifaddresses(iface)
                interface_info[iface] = addrs
        except ImportError:
            interface_info = "netifaces-not-available"
        except Exception as e:
            interface_info = f"error: {str(e)}"
        
        return {
            "status": "success",
            "instance_id": instance_id,
            "interfaces": interface_info,
            "environment_vars": {
                "VPC_ID": os.environ.get('VPC_ID', 'not-set'),
                "SUBNET_IDS": os.environ.get('SUBNET_IDS', 'not-set'),
                "SECURITY_GROUP_IDS": os.environ.get('SECURITY_GROUP_IDS', 'not-set'),
                "AWS_LAMBDA_FUNCTION_NAME": os.environ.get('AWS_LAMBDA_FUNCTION_NAME', 'not-set'),
                "AWS_REGION": os.environ.get('AWS_REGION', 'not-set')
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/dns-test")
def dns_test():
    """Test DNS resolution capabilities"""
    import socket
    
    test_hosts = [
        "google.com",
        "amazonaws.com", 
        "rds.amazonaws.com",
        "secretsmanager.eu-west-1.amazonaws.com",
        "ssm.eu-west-1.amazonaws.com"
    ]
    
    results = {}
    
    for host in test_hosts:
        try:
            start_time = time.time()
            ip = socket.gethostbyname(host)
            duration = time.time() - start_time
            results[host] = {
                "status": "success",
                "ip": ip,
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            results[host] = {
                "status": "error", 
                "error": str(e)
            }
    
    return {
        "status": "success",
        "dns_tests": results,
        "timestamp": time.time()
    }

@app.get("/network-test")
def network_test():
    """Test network connectivity to various endpoints"""
    import urllib.request
    import urllib.error
    
    test_urls = [
        "https://httpbin.org/ip",
        "https://www.google.com",
        "https://amazonaws.com",
        "https://ssm.eu-west-1.amazonaws.com",
        "https://secretsmanager.eu-west-1.amazonaws.com"
    ]
    
    results = {}
    
    for url in test_urls:
        try:
            start_time = time.time()
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'lambda-network-test')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                content_length = len(response.read())
                duration = time.time() - start_time
                
                results[url] = {
                    "status": "success",
                    "status_code": status_code,
                    "content_length": content_length,
                    "duration_ms": round(duration * 1000, 2)
                }
        except urllib.error.HTTPError as e:
            results[url] = {
                "status": "http_error",
                "status_code": e.code,
                "error": str(e)
            }
        except urllib.error.URLError as e:
            results[url] = {
                "status": "url_error",
                "error": str(e)
            }
        except Exception as e:
            results[url] = {
                "status": "error",
                "error": str(e)
            }
    
    return {
        "status": "success",
        "network_tests": results,
        "timestamp": time.time()
    }

@app.get("/network-simple-test")
def network_simple_test():
    """Simple network connectivity test"""
    try:
        # Test basic socket connectivity
        import socket
        
        # Test AWS services
        aws_tests = {}
        
        # Test SSM endpoint
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('ssm.eu-west-1.amazonaws.com', 443))
            duration = time.time() - start_time
            sock.close()
            
            aws_tests['ssm'] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            aws_tests['ssm'] = {"status": "error", "error": str(e)}
        
        # Test Secrets Manager endpoint  
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('secretsmanager.eu-west-1.amazonaws.com', 443))
            duration = time.time() - start_time
            sock.close()
            
            aws_tests['secrets_manager'] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            aws_tests['secrets_manager'] = {"status": "error", "error": str(e)}
        
        # Test basic HTTP connectivity
        try:
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('google.com', 80))
            duration = time.time() - start_time
            sock.close()
            
            aws_tests['internet'] = {
                "status": "success" if result == 0 else "failed",
                "result_code": result,
                "duration_ms": round(duration * 1000, 2)
            }
        except Exception as e:
            aws_tests['internet'] = {"status": "error", "error": str(e)}
        
        return {
            "status": "success",
            "simple_network_tests": aws_tests,
            "timestamp": time.time()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/api/v1/test")
def test_endpoint():
    """Test endpoint for API functionality"""
    return {
        "message": "API is working correctly",
        "timestamp": time.time(),
        "version": "1.0.0"
    }

@app.get("/env-debug")
def env_debug():
    """Debug environment variables (filtered for security)"""
    env_vars = {}
    
    # Safe environment variables to display
    safe_vars = [
        'AWS_REGION', 'AWS_LAMBDA_FUNCTION_NAME', 'AWS_LAMBDA_FUNCTION_VERSION',
        'AWS_LAMBDA_LOG_GROUP_NAME', 'AWS_LAMBDA_LOG_STREAM_NAME',
        'AWS_EXECUTION_ENV', 'AWS_LAMBDA_RUNTIME_API', 'AWS_LAMBDA_INITIALIZATION_TYPE',
        'AMPLIFY_ENV', 'AWS_BRANCH', 'LAMBDA_TASK_ROOT', 'LAMBDA_RUNTIME_DIR',
        'PATH', 'PWD', 'LANG', 'TZ'
    ]
    
    for var in safe_vars:
        env_vars[var] = os.environ.get(var, 'not-set')
    
    # Count total environment variables
    total_env_vars = len(os.environ)
    
    return {
        "status": "success",
        "safe_environment_variables": env_vars,
        "total_env_var_count": total_env_vars,
        "timestamp": time.time()
    }

# AWS Lambda handler
handler = Mangum(app) 