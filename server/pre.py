from tensorflow.keras.preprocessing import image

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Vamos importar as funções necessárias diretamente
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Flatten, Input
from resnet50 import ResNet50
import glob
import numpy as np

def bulid_model(input_shape, dropout, fc_layers, num_classes):
	inputs = Input(shape=input_shape, name='input_1')
	x = ResNet50(input_tensor=inputs)
	x = Flatten()(x)
	for fc in fc_layers:
		x = Dense(fc, activation='relu')(x)
	predictions = Dense(num_classes, activation='softmax')(x)
	model = Model(inputs=inputs, outputs=predictions)
	return model 

if __name__ == '__main__':

	img_h = 224
	img_w = 224
	input_shape = (224,224,3)
	fc_layers = [1024,1024]
	num_classes = 6
	image_path = 'test/'
	weights_path = 'C:\\facul\\6periodo\\lixo-2\\weights\\weights-029-0.83.weights.h5'  # Melhor modelo (menor loss)
	# Aceitar múltiplos formatos de imagem
	images = glob.glob(image_path+'*.jpg') + glob.glob(image_path+'*.jpeg') + glob.glob(image_path+'*.png') + glob.glob(image_path+'*.JPG')
	cls_list = ['cardboard','glass','metal','paper','plastic','trash']
	model = bulid_model(input_shape=input_shape,dropout=0,fc_layers=fc_layers,num_classes=num_classes)
	model.load_weights(weights_path)
	for f in images:
		img = image.load_img(f,target_size=(img_h,img_w))
		if img is None:
			continue

		x = image.img_to_array(img)
		x = np.expand_dims(x,axis=0)
		pred = model.predict(x)[0]
		top_inds = pred.argsort()[::-1][:5]
		print(f)
		for i in top_inds:
			print(' {:.3f}  {}'.format(pred[i],cls_list[i]))
