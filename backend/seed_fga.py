import asyncio
import yaml
import logging
import subprocess
from pathlib import Path
from app.config import settings
from app.utils.auth0_fga_client import fga_client
from openfga_sdk.client.models import ClientTuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("seed_fga")

async def deploy_model():
    """Deploy the authorization model using the FGA CLI."""
    logger.info("Deploying authorization model using FGA CLI...")
    
    # Ensure fga.exe exists
    fga_executable = Path("fga.exe")
    if not fga_executable.exists():
        logger.error("fga.exe not found in the backend directory. Cannot deploy model automatically.")
        return False
        
    cmd = [
        str(fga_executable.absolute()), "model", "write",
        "--file", "app/fga/model.fga.yaml"
    ]
    
    # Add auth flags from settings
    if settings.auth0_fga_store_id:
        cmd.extend(["--store-id", settings.auth0_fga_store_id])
    if settings.auth0_fga_api_url:
        cmd.extend(["--api-url", settings.auth0_fga_api_url])
    if settings.auth0_fga_client_id:
        cmd.extend(["--client-id", settings.auth0_fga_client_id])
    if settings.auth0_fga_client_secret:
        cmd.extend(["--client-secret", settings.auth0_fga_client_secret])
    if settings.auth0_fga_api_audience:
        cmd.extend(["--api-audience", settings.auth0_fga_api_audience])
    if settings.auth0_fga_api_token_issuer:
        cmd.extend(["--api-token-issuer", settings.auth0_fga_api_token_issuer])
    
    try:
        # Run FGA CLI
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("✅ Successfully deployed model!")
            if result.stdout:
                logger.info(f"Model details: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"❌ Failed to deploy model: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error executing FGA CLI: {e}")
        return False

async def main():
    logger.info("Starting FGA Seed Script...")
    
    # 1. Health check to verify connection
    logger.info("Checking Auth0 FGA connection...")
    is_healthy = await fga_client.health_check()
    if not is_healthy:
        logger.error(
            "❌ Failed to connect to Auth0 FGA. Please check your credentials and configuration."
        )
        return
        
    logger.info("✅ Auth0 FGA connection successful.")

    # 2. Deploy rules (authorization model)
    await deploy_model()

    # 3. Read the YAML file for tuples and tests
    yaml_path = Path("app/fga/model.fga.yaml")
    if not yaml_path.exists():
        logger.error(f"❌ Could not find FGA model file at {yaml_path}")
        return
        
    try:
        with open(yaml_path, "r") as f:
            fga_data = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"❌ Error parsing YAML: {e}")
        return

    # 4. Deploy tuples (seed data)
    if "tuples" in fga_data and fga_data["tuples"]:
        logger.info(f"Writing {len(fga_data['tuples'])} tuples from seed file...")
        tuples_to_write = []
        for t in fga_data["tuples"]:
            tuples_to_write.append(ClientTuple(
                user=t["user"],
                relation=t["relation"],
                object=t["object"]
            ))
            
        success = await fga_client.write_tuples(tuples_to_write)
        if success:
            logger.info("✅ Successfully wrote tuples.")
        else:
            logger.error("❌ Failed to write tuples.")
    else:
        logger.info("No tuples to write.")

    # 5. Run tests (assertions)
    if "tests" in fga_data and fga_data["tests"]:
        logger.info("Running FGA tests against Auth0...")
        for test_group in fga_data["tests"]:
            for check in test_group.get("check", []):
                user = check["user"]
                obj = check["object"]
                for relation, expected in check.get("assertions", {}).items():
                    result = await fga_client.check_permission(user, relation, obj)
                    if result == expected:
                        logger.info(
                            f"✅ PASS: {user} has relation '{relation}' to {obj} == {expected}"
                        )
                    else:
                        logger.error(
                            f"❌ FAIL: {user} has relation '{relation}' to {obj}. Expected {expected}, got {result}"
                        )
    else:
        logger.info("No tests to run.")
        
    # Cleanup
    await fga_client.close()

if __name__ == "__main__":
    asyncio.run(main())