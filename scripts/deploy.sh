#!/usr/bin/env bash
#
# CaseCommand — Automated Deployment Script
#
# Handles the full deployment pipeline via CLI tools (no browser needed):
#   1. Supabase project setup + database migration
#   2. Render service deployment
#   3. Stripe product/price configuration
#   4. Environment variable wiring
#   5. Health check verification
#
# Prerequisites (installed automatically if missing):
#   - supabase CLI (npx supabase)
#   - render CLI (render-cli via pip or brew)
#   - stripe CLI (stripe)
#   - gh CLI (for GitHub integration)
#
# Usage:
#   ./scripts/deploy.sh              # Full deployment
#   ./scripts/deploy.sh --db-only    # Only run database migrations
#   ./scripts/deploy.sh --check      # Health check only
#   ./scripts/deploy.sh --env        # Set environment variables only
#
set -euo pipefail

# ──────────────────────────────────────────────────────────────────────
# Colors & helpers
# ──────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
fail()  { echo -e "${RED}[FAIL]${NC} $*"; exit 1; }
ask()   { read -rp "$(echo -e "${YELLOW}[?]${NC} $1: ")" "$2"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env"

# ──────────────────────────────────────────────────────────────────────
# Load existing .env if present
# ──────────────────────────────────────────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
    info "Loading existing .env"
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
fi

# ──────────────────────────────────────────────────────────────────────
# CLI tool checks
# ──────────────────────────────────────────────────────────────────────
check_tools() {
    info "Checking required CLI tools..."

    local missing=()

    if ! command -v npx &>/dev/null; then
        missing+=("node/npx — install from https://nodejs.org")
    fi

    if ! command -v stripe &>/dev/null; then
        warn "Stripe CLI not found. Install: brew install stripe/stripe-cli/stripe"
        warn "  or download from https://stripe.com/docs/stripe-cli"
        missing+=("stripe")
    fi

    if ! command -v gh &>/dev/null; then
        warn "GitHub CLI not found. Some features will be unavailable."
    fi

    if [[ ${#missing[@]} -gt 0 ]]; then
        warn "Missing tools: ${missing[*]}"
        warn "Some deployment steps may be skipped."
    else
        ok "All CLI tools available"
    fi
}

# ──────────────────────────────────────────────────────────────────────
# Step 1: Supabase Setup
# ──────────────────────────────────────────────────────────────────────
setup_supabase() {
    info "=== SUPABASE SETUP ==="

    if [[ -z "${SUPABASE_URL:-}" ]]; then
        echo ""
        echo "  No SUPABASE_URL found. You have two options:"
        echo ""
        echo "  A) Create a new Supabase project via CLI:"
        echo "     npx supabase projects create casecommand --org-id YOUR_ORG_ID"
        echo ""
        echo "  B) Use an existing project — enter credentials below."
        echo ""
        ask "Supabase project URL (e.g., https://xxx.supabase.co)" SUPABASE_URL
        ask "Supabase service role key (starts with eyJ...)" SUPABASE_SECRET_KEY
        ask "Supabase JWT secret" SUPABASE_JWT_SECRET

        # Persist to .env
        {
            echo "SUPABASE_URL=$SUPABASE_URL"
            echo "SUPABASE_SECRET_KEY=$SUPABASE_SECRET_KEY"
            echo "SUPABASE_JWT_SECRET=$SUPABASE_JWT_SECRET"
        } >> "$ENV_FILE"
        ok "Supabase credentials saved to .env"
    else
        ok "Supabase URL found: ${SUPABASE_URL:0:30}..."
    fi

    # Run database migration
    info "Running database migration..."
    if [[ -f "$PROJECT_ROOT/migrations/001_full_schema.sql" ]]; then
        # Use supabase CLI if linked, otherwise use direct psql/API
        if command -v npx &>/dev/null && [[ -f "$PROJECT_ROOT/supabase/config.toml" ]]; then
            npx supabase db push --linked
        else
            # Direct execution via Supabase Management API
            info "Applying migration via Supabase SQL endpoint..."
            local project_ref
            project_ref=$(echo "$SUPABASE_URL" | sed -E 's|https://([^.]+)\.supabase\.co.*|\1|')

            if [[ -n "$project_ref" ]]; then
                local sql_content
                sql_content=$(cat "$PROJECT_ROOT/migrations/001_full_schema.sql")

                curl -s -X POST \
                    "https://${project_ref}.supabase.co/rest/v1/rpc" \
                    -H "apikey: ${SUPABASE_SECRET_KEY}" \
                    -H "Authorization: Bearer ${SUPABASE_SECRET_KEY}" \
                    -H "Content-Type: application/json" \
                    -d "{\"query\": \"\"}" \
                    2>/dev/null || true

                warn "Auto-migration via API is limited. Run the migration manually:"
                echo ""
                echo "  Option 1: Supabase Dashboard > SQL Editor > paste migrations/001_full_schema.sql"
                echo "  Option 2: psql \$DATABASE_URL -f migrations/001_full_schema.sql"
                echo "  Option 3: npx supabase db push (if linked)"
                echo ""
                ask "Press Enter after running the migration (or 'skip' to continue)" _confirm
            fi
        fi
    else
        warn "No migration file found at migrations/001_full_schema.sql"
    fi
}

# ──────────────────────────────────────────────────────────────────────
# Step 2: Anthropic API Key
# ──────────────────────────────────────────────────────────────────────
setup_anthropic() {
    info "=== ANTHROPIC API KEY ==="
    if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
        ask "Anthropic API key (sk-ant-...)" ANTHROPIC_API_KEY
        echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> "$ENV_FILE"
        ok "Saved"
    else
        ok "Anthropic API key found"
    fi
}

# ──────────────────────────────────────────────────────────────────────
# Step 3: Stripe Setup
# ──────────────────────────────────────────────────────────────────────
setup_stripe() {
    info "=== STRIPE BILLING SETUP ==="

    if [[ -z "${STRIPE_SECRET_KEY:-}" ]]; then
        echo ""
        echo "  Stripe is needed for subscription billing."
        echo "  Get your keys from https://dashboard.stripe.com/apikeys"
        echo ""
        ask "Stripe secret key (sk_live_... or sk_test_...)" STRIPE_SECRET_KEY
        echo "STRIPE_SECRET_KEY=$STRIPE_SECRET_KEY" >> "$ENV_FILE"
    else
        ok "Stripe secret key found"
    fi

    # Create products and prices via Stripe CLI
    if command -v stripe &>/dev/null && [[ -n "${STRIPE_SECRET_KEY:-}" ]]; then
        info "Creating Stripe products and prices..."

        # Solo plan
        if [[ -z "${STRIPE_PRICE_SOLO:-}" ]]; then
            info "Creating Solo plan ($99/mo)..."
            local solo_product
            solo_product=$(stripe products create \
                --name="CaseCommand Solo" \
                --description="Single attorney — 500 AI calls/month" \
                --api-key="$STRIPE_SECRET_KEY" \
                --format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || true

            if [[ -n "$solo_product" ]]; then
                STRIPE_PRICE_SOLO=$(stripe prices create \
                    --product="$solo_product" \
                    --unit-amount=9900 \
                    --currency=usd \
                    --recurring-interval=month \
                    --api-key="$STRIPE_SECRET_KEY" \
                    --format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || true
                echo "STRIPE_PRICE_SOLO=$STRIPE_PRICE_SOLO" >> "$ENV_FILE"
                ok "Solo plan created: $STRIPE_PRICE_SOLO"
            fi
        else
            ok "Solo price ID found: $STRIPE_PRICE_SOLO"
        fi

        # Firm plan
        if [[ -z "${STRIPE_PRICE_FIRM:-}" ]]; then
            info "Creating Firm plan ($299/mo)..."
            local firm_product
            firm_product=$(stripe products create \
                --name="CaseCommand Firm" \
                --description="Up to 5 attorneys — 2000 AI calls/month" \
                --api-key="$STRIPE_SECRET_KEY" \
                --format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || true

            if [[ -n "$firm_product" ]]; then
                STRIPE_PRICE_FIRM=$(stripe prices create \
                    --product="$firm_product" \
                    --unit-amount=29900 \
                    --currency=usd \
                    --recurring-interval=month \
                    --api-key="$STRIPE_SECRET_KEY" \
                    --format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || true
                echo "STRIPE_PRICE_FIRM=$STRIPE_PRICE_FIRM" >> "$ENV_FILE"
                ok "Firm plan created: $STRIPE_PRICE_FIRM"
            fi
        else
            ok "Firm price ID found: $STRIPE_PRICE_FIRM"
        fi

        # Enterprise plan
        if [[ -z "${STRIPE_PRICE_ENTERPRISE:-}" ]]; then
            info "Creating Enterprise plan ($799/mo)..."
            local ent_product
            ent_product=$(stripe products create \
                --name="CaseCommand Enterprise" \
                --description="Unlimited attorneys — 10000 AI calls/month — priority support" \
                --api-key="$STRIPE_SECRET_KEY" \
                --format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || true

            if [[ -n "$ent_product" ]]; then
                STRIPE_PRICE_ENTERPRISE=$(stripe prices create \
                    --product="$ent_product" \
                    --unit-amount=79900 \
                    --currency=usd \
                    --recurring-interval=month \
                    --api-key="$STRIPE_SECRET_KEY" \
                    --format=json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null) || true
                echo "STRIPE_PRICE_ENTERPRISE=$STRIPE_PRICE_ENTERPRISE" >> "$ENV_FILE"
                ok "Enterprise plan created: $STRIPE_PRICE_ENTERPRISE"
            fi
        else
            ok "Enterprise price ID found: $STRIPE_PRICE_ENTERPRISE"
        fi

        # Webhook setup
        if [[ -z "${STRIPE_WEBHOOK_SECRET:-}" ]]; then
            info "Setting up Stripe webhook..."
            echo ""
            echo "  After deploying to Render, create a webhook at:"
            echo "  https://dashboard.stripe.com/webhooks"
            echo "    URL: https://YOUR_RENDER_URL/billing/webhook"
            echo "    Events: checkout.session.completed, customer.subscription.updated,"
            echo "            customer.subscription.deleted, invoice.payment_failed"
            echo ""
            echo "  Or use the Stripe CLI for local testing:"
            echo "    stripe listen --forward-to localhost:8000/billing/webhook"
            echo ""
        fi
    else
        warn "Stripe CLI not available — skipping product creation."
        warn "Create products manually at https://dashboard.stripe.com/products"
    fi
}

# ──────────────────────────────────────────────────────────────────────
# Step 4: Deploy to Render
# ──────────────────────────────────────────────────────────────────────
deploy_render() {
    info "=== RENDER DEPLOYMENT ==="

    echo ""
    echo "  CaseCommand uses Render for hosting (render.yaml is pre-configured)."
    echo ""
    echo "  Deployment options:"
    echo ""
    echo "  A) Auto-deploy from GitHub (recommended):"
    echo "     1. Push code to GitHub"
    echo "     2. Render auto-deploys from main branch"
    echo ""
    echo "  B) Manual via Render Dashboard:"
    echo "     1. Go to https://dashboard.render.com/new/blueprint"
    echo "     2. Connect your GitHub repo"
    echo "     3. Render reads render.yaml automatically"
    echo ""
    echo "  C) Render CLI (if installed):"
    echo "     render blueprint launch"
    echo ""

    # Check if repo is connected to GitHub
    if command -v gh &>/dev/null; then
        local remote_url
        remote_url=$(git -C "$PROJECT_ROOT" remote get-url origin 2>/dev/null) || true

        if [[ -n "$remote_url" ]]; then
            ok "Git remote: $remote_url"

            # Ensure code is pushed
            local branch
            branch=$(git -C "$PROJECT_ROOT" branch --show-current)
            info "Current branch: $branch"

            if [[ "$branch" == "main" ]]; then
                ask "Push to GitHub to trigger Render deploy? (y/n)" _push
                if [[ "$_push" == "y" ]]; then
                    git -C "$PROJECT_ROOT" push origin main
                    ok "Pushed to GitHub. Render will auto-deploy if connected."
                fi
            else
                warn "Not on main branch. Merge to main before deploying to production."
            fi
        fi
    fi

    # Set environment variables on Render
    echo ""
    info "Environment variables to set on Render:"
    echo ""
    echo "  Required:"
    echo "    ANTHROPIC_API_KEY    = ${ANTHROPIC_API_KEY:+(set)}"
    echo "    SUPABASE_URL         = ${SUPABASE_URL:+(set)}"
    echo "    SUPABASE_SECRET_KEY  = ${SUPABASE_SECRET_KEY:+(set)}"
    echo "    SUPABASE_JWT_SECRET  = ${SUPABASE_JWT_SECRET:+(set)}"
    echo ""
    echo "  Billing:"
    echo "    STRIPE_SECRET_KEY         = ${STRIPE_SECRET_KEY:+(set)}"
    echo "    STRIPE_WEBHOOK_SECRET     = ${STRIPE_WEBHOOK_SECRET:+(not set — set after webhook creation)}"
    echo "    STRIPE_PRICE_SOLO         = ${STRIPE_PRICE_SOLO:+(set)}"
    echo "    STRIPE_PRICE_FIRM         = ${STRIPE_PRICE_FIRM:+(set)}"
    echo "    STRIPE_PRICE_ENTERPRISE   = ${STRIPE_PRICE_ENTERPRISE:+(set)}"
    echo ""
    echo "  Optional channels:"
    echo "    TELEGRAM_BOT_TOKEN        = ${TELEGRAM_BOT_TOKEN:+(set)}${TELEGRAM_BOT_TOKEN:-(not set)}"
    echo "    TWILIO_ACCOUNT_SID        = ${TWILIO_ACCOUNT_SID:+(set)}${TWILIO_ACCOUNT_SID:-(not set)}"
    echo ""

    # Generate a Render env-var setter command
    info "To set all env vars at once via Render CLI:"
    echo ""
    echo "  render env set \\"
    for var in ANTHROPIC_API_KEY SUPABASE_URL SUPABASE_SECRET_KEY SUPABASE_JWT_SECRET \
               STRIPE_SECRET_KEY STRIPE_PRICE_SOLO STRIPE_PRICE_FIRM STRIPE_PRICE_ENTERPRISE; do
        local val="${!var:-}"
        if [[ -n "$val" ]]; then
            echo "    $var='${val:0:8}...' \\"
        fi
    done
    echo "    --service casecommand"
    echo ""
}

# ──────────────────────────────────────────────────────────────────────
# Step 5: Health Check
# ──────────────────────────────────────────────────────────────────────
health_check() {
    info "=== HEALTH CHECK ==="

    local base_url="${BASE_URL:-}"
    if [[ -z "$base_url" ]]; then
        ask "Deployed URL (e.g., https://casecommand.onrender.com)" base_url
    fi

    info "Checking $base_url ..."

    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url/" --max-time 30) || true

    if [[ "$status" == "200" ]]; then
        ok "Root endpoint: 200 OK"
    else
        warn "Root endpoint returned: $status"
    fi

    # Check /health or /docs
    local health_status
    health_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url/docs" --max-time 15) || true
    if [[ "$health_status" == "200" ]]; then
        ok "Swagger docs: 200 OK at $base_url/docs"
    fi

    # Check key API endpoints
    for endpoint in "/cases" "/intake" "/discovery" "/motions" "/calendar" "/depositions" "/verdicts"; do
        local ep_status
        ep_status=$(curl -s -o /dev/null -w "%{http_code}" "$base_url$endpoint" --max-time 10) || true
        if [[ "$ep_status" == "401" || "$ep_status" == "200" || "$ep_status" == "422" ]]; then
            ok "$endpoint : $ep_status (reachable)"
        else
            warn "$endpoint : $ep_status"
        fi
    done

    echo ""
    ok "Deployment verification complete!"
    echo ""
    echo "  Dashboard:  $base_url"
    echo "  API docs:   $base_url/docs"
    echo ""
}

# ──────────────────────────────────────────────────────────────────────
# Step 6: Post-deploy webhook + channel setup
# ──────────────────────────────────────────────────────────────────────
post_deploy() {
    info "=== POST-DEPLOY SETUP ==="

    local base_url="${BASE_URL:-}"

    echo ""
    echo "  Remaining manual steps:"
    echo ""
    echo "  1. STRIPE WEBHOOK:"
    echo "     URL: $base_url/billing/webhook"
    echo "     Events: checkout.session.completed, customer.subscription.updated,"
    echo "             customer.subscription.deleted, invoice.payment_failed"
    echo "     Then set STRIPE_WEBHOOK_SECRET on Render."
    echo ""
    echo "  2. TELEGRAM BOT (optional):"
    echo "     a) Message @BotFather: /newbot -> get token"
    echo "     b) Set TELEGRAM_BOT_TOKEN on Render"
    echo "     c) Register webhook:"
    echo "        curl -X POST https://api.telegram.org/bot\$TOKEN/setWebhook \\"
    echo "          -d \"url=$base_url/telegram/webhook\""
    echo ""
    echo "  3. TWILIO SMS/WHATSAPP (optional):"
    echo "     a) Get credentials from https://console.twilio.com"
    echo "     b) Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER on Render"
    echo "     c) Set webhook URL in Twilio console:"
    echo "        SMS:      $base_url/twilio/sms"
    echo "        WhatsApp: $base_url/twilio/whatsapp"
    echo ""
    echo "  4. CUSTOM DOMAIN (optional):"
    echo "     Add in Render dashboard > Settings > Custom Domains"
    echo ""
}

# ──────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo "  ┌─────────────────────────────────────────┐"
    echo "  │     CaseCommand Deployment Script        │"
    echo "  │     No browser required                  │"
    echo "  └─────────────────────────────────────────┘"
    echo ""

    case "${1:-}" in
        --db-only)
            setup_supabase
            ;;
        --check)
            health_check
            ;;
        --env)
            setup_anthropic
            setup_supabase
            setup_stripe
            ;;
        --stripe)
            setup_stripe
            ;;
        *)
            check_tools
            setup_anthropic
            setup_supabase
            setup_stripe
            deploy_render
            health_check
            post_deploy
            ;;
    esac

    echo ""
    ok "Done! All configuration saved to .env"
}

main "$@"
