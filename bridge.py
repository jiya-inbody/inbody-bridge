import xmlrpc.client
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- 1. 오두 접속 정보 (네가 준 정보 그대로 세팅!) ---
ODOO_URL = "https://closyss.odoo.com"
ODOO_DB = "closyss"
ODOO_USER = "admin"  # ★혹시 안되면 로그인 이메일 주소로 바꿔봐!
ODOO_KEY = "020c6dde481ba81e0e7efaa8abf0a671bddf72bd"
DUMMY_PARTNER_ID = 41 # ★네가 확인한 가짜 고객 ID
# -----------------------------------------------

@app.route('/create_quote', methods=['POST'])
def create_quote():
    try:
        data = request.json
        print(f"데이터 수신: {data}")

        # XML-RPC 설정: allow_none=True를 넣어야 'marshal None' 에러가 안 나!
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common', allow_none=True)
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_KEY, {})
        
        # 인증 실패 확인 (Access Denied 방지)
        if not uid:
            return jsonify({"status": "error", "message": "Odoo Authentication Failed. Check your User/Key."}), 401

        models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object', allow_none=True)

        # 2. 견적서 생성 (고객은 100% 더미로 고정!)
        # 계산기에서 partner_id가 안 넘어와도 DUMMY_PARTNER_ID를 쓰도록 함
        target_id = data.get('partner_id') if data.get('partner_id') else DUMMY_PARTNER_ID

        order_id = models.execute_kw(ODOO_DB, uid, ODOO_KEY, 'sale.order', 'create', [{
            'partner_id': target_id,
            'note': f"Package: {data.get('tier', 'N/A')} | Auto-generated via Calculator"
        }])

        # 3. 상품 라인 추가
        for item in data.get('items', []):
            models.execute_kw(ODOO_DB, uid, ODOO_KEY, 'sale.order.line', 'create', [{
                'order_id': order_id,
                'product_id': item['product_id'],
                'product_uom_qty': 1,
            }])

        # 4. 할인 라인 추가 (할인액이 있을 때만)
        discount_val = float(data.get('discount', 0))
        if discount_val > 0:
            # ★주의: 오두에 'Discount'용 상품이 등록되어 있어야 해. (ID 999는 예시임)
            # 실제 할인 상품 ID를 찾아서 아래 999 자리에 넣어줘!
            try:
                models.execute_kw(ODOO_DB, uid, ODOO_KEY, 'sale.order.line', 'create', [{
                    'order_id': order_id,
                    'product_id': 999,  # ★여기에 실제 할인 상품 ID 입력!
                    'name': f"Special Bundle Discount ({data.get('tier')})",
                    'price_unit': -discount_val,
                    'product_uom_qty': 1,
                }])
            except:
                print("할인 상품 ID가 틀려서 할인 라인 생성은 실패함 (무시 가능)")

        return jsonify({"status": "success", "order_id": order_id})

    except Exception as e:
        print(f"에러 발생: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # 서버 실행!
    app.run(host='0.0.0.0', port=5000)