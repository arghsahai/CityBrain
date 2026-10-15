"""Optional browser QA. Install playwright; requires Chrome or its Chromium build."""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8770')
    parser.add_argument('--output',type=Path,default=Path('docs/chennai'))
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(channel='chrome',headless=True,
            args=['--use-angle=gl','--enable-webgl','--ignore-gpu-blocklist'])
        page=browser.new_page(viewport={'width':1440,'height':950},device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url,wait_until='domcontentloaded')
        expect(page.locator('#mode')).to_contain_text('REPLAY',timeout=60000)
        page.locator('#seek').fill('200')
        page.locator('#seek').dispatch_event('input')
        expect(page.locator('#time')).to_have_text('200 s',timeout=30000)
        page.wait_for_timeout(1500)
        assert not page.locator('#fallback').is_visible(),page.locator('#notice').inner_text()
        assert page.evaluate('Boolean(viewer && viewer.scene.canvas && !fallbackMode)')
        assert page.evaluate('vehicles.size')>10
        assert page.evaluate('signals.size')==2
        assert page.evaluate('routeEntity.polyline.positions.getValue(viewer.clock.currentTime).length')>2
        first=page.locator('#ambulance').inner_text()
        page.screenshot(path=str(args.output/'desktop.png'))
        page.locator('#seek').fill('220')
        page.locator('#seek').dispatch_event('input')
        expect(page.locator('#time')).to_have_text('220 s',timeout=30000)
        assert page.locator('#ambulance').inner_text()!=first
        page.locator('#flat').click()
        assert page.locator('#fallback').is_visible()
        assert page.locator('#fallback polyline').count()>700
        page.screenshot(path=str(args.output/'fallback.png'))
        page.locator('#seek').fill('759')
        page.locator('#seek').dispatch_event('input')
        expect(page.locator('#outcome')).to_contain_text('SUCCESS',timeout=30000)
        page.set_viewport_size({'width':800,'height':1000})
        page.screenshot(path=str(args.output/'tablet.png'))
        assert not errors,errors
        result=dict(errors=errors,status=page.locator('#outcome').inner_text(),
            checks=['Cesium WebGL scene','moving observed ambulance','visible vehicles and both signals',
                    'accepted route geometry','SVG fallback','replay time filtering','terminal SUCCESS','800px layout'],
            browser=browser.version)
        (args.output/'browser-check.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
        browser.close()


if __name__=='__main__':
    main()
