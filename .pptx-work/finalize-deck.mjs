import path from 'node:path';
import { pathToFileURL } from 'node:url';
const workspaceDir='C:/Users/MKREDDY/AI_builder_cup/foodbridge_v2';
const skillDir='C:/Users/MKREDDY/.codex/plugins/cache/openai-primary-runtime/presentations/26.1015.12040/skills/presentations';
const finalPath=path.join(workspaceDir,'submission-output/FoodBridge_RescueFlow_AI_Builder_Cup.pptx');
const {finalizePresentation}=await import(pathToFileURL(path.join(skillDir,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({
  workspaceDir,
  candidatePath:path.join(workspaceDir,'.pptx-work/candidate.pptx'),
  finalPath,
  pythonExecutable:'C:/Users/MKREDDY/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
  integrityValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skillDir,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','9144000,5143500','--validate-bullet-geometry','--validate-heading-fit'],
  explicitTotalSlideCount:16,
  fontPolicy:{basis:'reference',families:['Google Sans Flex','Google Sans Flex Medium','Google Sans Flex SemiBold'],referencePath:'C:/Users/MKREDDY/Downloads/Submission Template _ AI Builder Cup.pptx',referenceSha256:'0bf6153e0fad7c76016f82acb19a4c8545a2ea58138b72340fb80c61b85c0e78'},
  verifyArtifactToolImport:true,
  receiptPath:path.join(workspaceDir,'.pptx-work/validation.json'),
});
console.log(JSON.stringify({finalPath,result},null,2));
