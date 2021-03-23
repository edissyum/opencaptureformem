<?php
// NCH01
namespace Attachment\controllers;

use Convert\controllers\ConvertPdfController;
use Slim\Http\Request;
use Slim\Http\Response;
use Attachment\models\AttachmentModel;
use Resource\models\ResModel;
use Resource\controllers\ResController;
use Respect\Validation\Validator;
use History\controllers\HistoryController;
use Resource\controllers\StoreController;
use SrcCore\models\CoreConfigModel;

class ReconciliationController
{
    public function create(Request $request, Response $response)
    {
        $data = $request->getParams();
        $check = Validator::notEmpty()->validate($data['encodedFile']);
        $check = $check && Validator::stringType()->notEmpty()->validate($data['chrono']);
        if (!$check) {
            return $response->withStatus(400)->withJson(['errors' => 'Bad Request']);
        }

        $resId = ReconciliationController::getWs($data);

        if (empty($resId) || !empty($resId['errors'])) {
            return $response->withStatus(500)->withJson(['errors' => '[ReconciliationController create] ' . $resId['errors']]);
        }

        HistoryController::add([
            'tableName' => 'res_attachments',
            'recordId'  => $resId,
            'eventType' => 'ADD',
            'info'      => _DOC_ADDED,
            'moduleId'  => 'reconciliation',
            'eventId'   => 'attachmentadd',
        ]);

        return $response->withJson(['resId' => $resId]);
    }

    public static function getWs($aArgs)
    {
        $identifier     = $aArgs['chrono'];
        $encodedContent = $aArgs['encodedFile'];

        $info = AttachmentModel::get([
            'select'  => ['res_id', 'title', 'res_id_master', 'recipient_id'],
            'where'   => ['identifier = ?', "status IN ('A_TRA', 'NEW','TMP')"],
            'data'    => [$identifier],
            'orderBy' => ['res_id DESC']
        ])[0];

        if (!Validator::intVal()->validate($info['res_id_master']) || !ResController::hasRightByResId(['resId' => [$info['res_id_master']], 'userId' => $GLOBALS['id']])) {
            return ['errors' => 'Document out of perimeter'];
        }

        if (!$info) {
            return ['errors' => 'No attachment'];
        }

        $title           = $info['title'];
        $fileFormat      = 'pdf';
        $attachment_type = $aArgs['attachment_type'] ?? 'signed_response';
        $res_id_master   = $info['res_id_master'];
        $status          = $aArgs['status'] ?? 'SIGN';

        $aArgs = [
            'title'        => $title,
            'encodedFile'  => $encodedContent,
            'format'       => $fileFormat,
            'typist'       => 'superadmin',
            'resIdMaster'  => $res_id_master,
            'type'         => $attachment_type,
            'chrono'       => $identifier,
            'recipientId'  => $info['recipient_id'],
            'status'       => $status,
            'originId'     => $info['res_id']
        ];

        $resId = StoreController::storeAttachment($aArgs);

        ConvertPdfController::convert([
            'resId'     => $resId,
            'collId'    => 'attachments_coll'
        ]);

        $customId = CoreConfigModel::getCustomId();
        $customId = empty($customId) ? 'null' : $customId;
        exec("php src/app/convert/scripts/FullTextScript.php --customId {$customId} --resId {$resId} --collId attachments_coll --userId {$GLOBALS['id']} > /dev/null &");

        // Suppression du projet de reponse
        $loadedXml = CoreConfigModel::getXmlLoaded(['path' => 'modules/attachments/xml/config.xml']);
        if ($loadedXml) {
            $reconciliationConfig    = $loadedXml->RECONCILIATION->CONFIG;
            $close_incoming          = $reconciliationConfig->close_incoming;

            AttachmentModel::update([
                'set'   => ['status' => 'SIGN'],
                'where' => ['res_id = ?'],
                'data'  => [$info['res_id']],
            ]);

            // Cloture du courrier entrant
            if ($close_incoming == 'true') {
                ResModel::update([
                    'set'   => ['status' => 'END'],
                    'where' => ['res_id = ?'],
                    'data'  => [$res_id_master],
                ]);
            }
        }

        return $resId;
    }

    public function checkAttachment(Request $request, Response $response)
    {
        $data = $request->getParams();

        $check = Validator::stringType()->notEmpty()->validate($data['chrono']);
        if (!$check) {
            return $response->withStatus(400)->withJson(['errors' => 'Bad Request']);
        }

        $attachment = AttachmentModel::get([
            'select'  => ['res_id_master'],
            'where'   => ['identifier = ?', "status IN ('A_TRA', 'NEW','TMP')"],
            'data'    => [$data['chrono']],
            'orderBy' => ['res_id DESC']
        ])[0];

        if (!Validator::intVal()->validate($attachment['res_id_master']) || !ResController::hasRightByResId(['resId' => [$attachment['res_id_master']], 'userId' => $GLOBALS['id']])) {
            return $response->withStatus(403)->withJson(['errors' => 'Document out of perimeter']);
        }

        if ($attachment == false) {
            return $response->withStatus(500)->withJson(['errors' => '[ReconciliationController checkAttachment] ' . _NO_ATTACHMENT_CHRONO]);
        } else {
            return $response->withJson(array('result' => 'OK'));
        }
    }
}
// END NCH01