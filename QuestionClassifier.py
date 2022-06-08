
from cmath import log
from enum import Enum
from py2neo import Graph
import ahocorasick
import logging

class QUESTIONTYPE(Enum):
    '''
    已知疾病，判断疾病的症状
    '''
    DISEASE_TO_SYMPTOM = 'disease_symptom'

    '''
    已知症状，判断疾病
    没有找到症状的问题类型，也用这个
    '''
    SYMPTOM_TO_DISEASE = 'symptom_disease'

    '''
    已知疾病，查找原因
    '''
    DISEASE_CAUSE = 'disease_cause'

    '''
    疾病的并发症
    '''
    DISEASE_COMLICATION = 'disease_complication'

    '''
    疾病的常用药物
    '''
    DISEASE_DRUG = 'disease_drug'

    '''
    已知疾病，不可食用食物
    '''
    DISEASE_AOID_FOOD = "disease_avoid_food"

    '''
    已知疾病，可使用食物
    '''
    DISEASE_GOOD_FOOD = "disease_good_food"

    '''
    已知疾病，查找检查项目
    '''
    DISEASE_DO_CHECK = 'disease_check'

    '''
    已知疾病，查询预防措施
    '''
    DISEASE_PREVENT = 'disease_prevent'

    '''
    疾病治疗方法
    '''
    DISEASE_TREAT_WAY = 'disease_treat_way'

    '''
    疾病治疗可能性
    '''
    DISEASE_CURED_PRO = 'disease_cured_prob'

    '''
    疾病科室
    '''
    DISEASE_TO_DEPARTMENT = 'disease_department'

    '''
    疾病治疗周期
    '''
    DISEASE_TREAT_CYCLE = 'disease_treat_cycle'

    '''
    已知疾病信息，但是没有问题类型
    '''
    DISEASE_DESC = 'disease_desc'

    '''
    判断不出来
    '''
    OTHER = 'match none type'

class ENTITYTYPE(Enum):
    DISEASE = "Disease"
    DEPARTMENT = "Department"
    CHECK = "Check"
    DRUG = "drug"
    FOOD = "food"
    SYMPTOM = "Symptom"



class QuestionClassifier(object):
    '''
    判断器初始化
    '''
    def __init__(self):
		# 实体加载
        # 疾病实体
        disease_path = ('data/region_words/diseases.txt')
        # 症状实体
        symptom_path = ('data/region_words/symptoms.txt')
        # 科室实体
        department_path = ('data/region_words/departments.txt')
        # 检查实体
        check_path =  ('data/region_words/checks.txt')
        # 药品实体
        drug_path = ('data/region_words/drugs.txt')
        # 食物实体
        food_path =  ('data/region_words/foods.txt')
        # 加载特征词
        print('initialing regional words')
        print('load diseases...')
        self.disease_words = [word.strip() for word in open(disease_path, encoding='utf-8') if word.strip()]
        print('load department...')
        self.department_words = [word.strip() for word in open(department_path, encoding='utf-8') if word.strip()]
        print('load check words...')
        self.check_words = [word.strip() for word in open(check_path, encoding='utf-8') if word.strip()]
        print('load drug words...')
        self.drug_words = [word.strip() for word in open(drug_path, encoding='utf-8') if word.strip()]
        print('load foods words...')
        self.food_words = [word.strip() for word in open(food_path, encoding='utf-8') if word.strip()]
        print('load symptom...')
        self.symptom_words = [word.strip() for word in open(symptom_path, encoding='utf-8') if word.strip()]

        # 构建领域词典
        self.region_words = set(self.disease_words+self.department_words+self.check_words+self.drug_words+self.food_words+self.symptom_words)
        # 构建actree
        print('building actree')
        self.region_tree= self.build_actree(self.region_words)
        # 构建实体类型字典
        self.word_type_dict = self.build_word_type_dict()


        
        # 加载类型否定词
        deny_path = ('data/region_words/deny.txt')
        self.deny_words = [word.strip() for word in open(deny_path, encoding='utf-8') if word.strip()]

        # 构建不同问题类型的问题触发词
        # 用于询问疾病的症状触发词，询问症状对应的疾病触发词
        self.symptom_qwds = ['症状', '表征', '现象', '症候', '表现','什么样','怎么回事']
        # 疾病的原因触发词
        self.cause_qwds = ['原因', '成因', '为什么', '怎么会', '怎样才', '咋样才', '怎样会', '如何会', '为啥', '为何', '如何才会', '怎么才会', '会导致',
						   '会造成','怎么回事','总是','老是']
        # 询问疾病并发症的触发词
        self.complication_qwds = ['并发症', '并发', '一起发生', '一并发生', '一起出现', '一并出现', '一同发生', '一同出现', '伴随发生', '伴随', '共现']
        # 疾病相关食品触发词
        self.food_qwds = ['饮食', '饮用', '吃', '食', '伙食', '膳食', '喝', '菜', '忌口', '补品', '保健品', '食谱', '菜谱', '食用', '食物', '补品']
        # 疾病治疗药物触发词
        self.drug_qwds = ['药', '药品', '用药', '胶囊', '口服液', '炎片','什么药']
        # 疾病预防触发词
        self.prevent_qwds = ['预防', '防范', '抵制', '抵御', '防止', '躲避', '逃避', '避开', '免得', '逃开', '避开', '避掉', '躲开', '躲掉', '绕开',
							 '怎样才能不', '怎么才能不', '咋样才能不', '咋才能不', '如何才能不',
							 '怎样才不', '怎么才不', '咋样才不', '咋才不', '如何才不',
							 '怎样才可以不', '怎么才可以不', '咋样才可以不', '咋才可以不', '如何可以不',
							 '怎样才可不', '怎么才可不', '咋样才可不', '咋才可不', '如何可不']
        # 疾病治疗周期触发词
        self.treat_cycle_qwds = ['周期', '多久', '多长时间', '多少时间', '几天', '几年', '多少天', '多少小时', '几个小时', '多少年']
        # 疾病治疗方式触发词
        self.treat_way_qwds = ['怎么治疗', '如何医治', '怎么医治', '怎么治', '怎么医', '如何治', '医治方式', '疗法', '咋治', '怎么办', '咋办', '咋治','治疗方式']
        # 疾病治愈概率触发词
        self.cure_prob_qwds = ['多大概率能治好', '多大几率能治好', '治好希望大么', '几率', '几成', '比例', '可能性', '能治', '可治', '可以治', '可以医','概率']
        # 疾病检查项目触发词
        self.check_qwds = ['检查', '检查项目', '查出', '检查', '测出', '试出','怎么查','查什么']
        # 疾病所属科室触发词
        self.belong_qwds = ['属于什么科', '属于', '什么科', '科室','挂号','挂什么','挂什么科室']
        
    
    def classify_main(self,question):
        '''
		:param question:
		:return: dict
		keywords : 问题中的关键词以及其对应实体类型（标签）
		question_types : 根据关键词及问题词（qwds） 判断问句类别（eg。 已知疾病找药物）
		'''
        keywords = self.get_keyword_from_question(question)

        if not keywords: # 如果问句中没有匹配的关键词，则无效问题（无法回答）
            return {}
        
        logging.info('本次匹配的entity包括：',keywords)

        data = {}
        data['keywords'] = keywords
        types = []
        # 收集问句当中所涉及到的实体类型
        for type in keywords.values():
            types += type
        
        question_types = []

        #TODO 1 已知疾病，判断症状
        if self.check_qwds_type(self.symptom_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_TO_SYMPTOM)
        
        #TODO 2 已知症状,判断疾病
        if self.check_qwds_type(self.symptom_qwds,question) and (ENTITYTYPE.SYMPTOM in types):
            question_types.append(QUESTIONTYPE.SYMPTOM_TO_DISEASE)
        
        #TODO 3 已知疾病，判断原因
        if self.check_qwds_type(self.cause_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_CAUSE)
        
        #TODO 4 已知疾病，判断并发症
        if self.check_qwds_type(self.complication_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_COMLICATION)

        #TODO 5 已知疾病，查找药品
        if self.check_qwds_type(self.drug_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_DRUG)
        
        #TODO 6 已知疾病，推荐或拒绝食物
        if self.check_qwds_type(self.food_qwds,question) and (ENTITYTYPE.DISEASE in types):
            is_deny = self.check_qwds_type(self.deny_words,question)
            if is_deny:
                question_types.append(QUESTIONTYPE.DISEASE_AOID_FOOD)
            else:
                question_types.append(QUESTIONTYPE.DISEASE_GOOD_FOOD)

        #TODO 7 已知疾病，查询就检查项目
        if self.check_qwds_type(self.check_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_DO_CHECK)
        
        #TODO 8 已知疾病，查询预防措施
        if self.check_qwds_type(self.prevent_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_PREVENT)
        
        #TODO 9 已知疾病，查找治愈方法
        if self.check_qwds_type(self.treat_way_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_TREAT_WAY)
        
        #TODO 10 已知疾病，查找治愈周期
        if self.check_qwds_type(self.treat_cycle_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_TREAT_CYCLE)

        #TODO 11 已知疾病，查找治愈可能性
        if self.check_qwds_type(self.cure_prob_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_CURED_PRO)

        #TODO 12 已知疾病，查找科室
        if self.check_qwds_type(self.belong_qwds,question) and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_TO_DEPARTMENT)
        
        # 知道疾病，但是无法判断，所以返回描述
        if question_types == [] and (ENTITYTYPE.DISEASE in types):
            question_types.append(QUESTIONTYPE.DISEASE_DESC)

        # 知道症状，但是无法判断问题类型,返回疾病对应的症状
        if question_types == [] and (ENTITYTYPE.SYMPTOM in types):
            question_types.append(QUESTIONTYPE.SYMPTOM_TO_DISEASE)
        
        data['question_types'] = question_types
        
        return data

    
    def check_qwds_type(self,words,sent):
        '''基于特征词进行分类'''
        for word in words:
            if word in sent:
                return True
        return False

    def get_keyword_from_question(self,question):
        region_words = []

        for item in self.region_tree.iter(question):
            keyword = item[1][1]
            region_words.append(keyword)
        region_words = list(set(region_words))

        # 同时匹配到长实体和短实体时候，去掉短实体，保留长实体
        stop_words = []
        for wd1 in region_words:
            for wd2 in region_words:
                if wd1 in wd2 and wd1 != wd2:
                    stop_words.append(wd1)
        # 去掉短实体
        final_words = [word for word in region_words if word not in stop_words]
        final_word_types = {word:self.word_type_dict.get(word) for word in final_words}
        return final_word_types

    '''
    :return: dict
    一个词可能对应多种标签类型 (eg. 肺栓塞 ['Disease', 'Symptom'])
    '''
    def build_word_type_dict(self):
        word_dict = dict()

        for word in self.region_words:
            word_dict[word] = []
            if word in self.disease_words:
                word_dict[word].append(ENTITYTYPE.DISEASE)

            if word in self.department_words:
                word_dict[word].append(ENTITYTYPE.DEPARTMENT)

            if word in self.check_words:
                word_dict[word].append(ENTITYTYPE.DEPARTMENT)

            if word in self.drug_words:
                word_dict[word].append(ENTITYTYPE.DRUG)

            if word in self.food_words:
                word_dict[word].append(ENTITYTYPE.FOOD)

            if word in self.symptom_words:
                word_dict[word].append(ENTITYTYPE.SYMPTOM)
        return word_dict

    '''
    构建actree
    '''
    def build_actree(self,word_list):
        actree = ahocorasick.Automaton()
        for ind, word in enumerate(word_list):
            actree.add_word(word, (ind, word))
            actree.make_automaton()
        return actree


class QuestionParser:

    def __init__(self) -> None:
        pass

    def parser_main(self,question_classify_res):
        keywords = question_classify_res['keywords']
        entity_dict = self.extract_entity(keywords)
        question_type_list = question_classify_res['question_types']

        sql_list = []
        for question_type in question_type_list:
            sql = []
            # 已知疾病，查询症状
            if question_type == QUESTIONTYPE.DISEASE_TO_SYMPTOM :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 已知症状，查询疾病
            if question_type == QUESTIONTYPE.SYMPTOM_TO_DISEASE :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.SYMPTOM))
            # 已知疾病，查原因
            if question_type == QUESTIONTYPE.DISEASE_CAUSE :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 已知疾病，查并发症
            if question_type == QUESTIONTYPE.DISEASE_COMLICATION :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 已知疾病，查常用药品
            if question_type == QUESTIONTYPE.DISEASE_DRUG :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 已知疾病，查推荐食物
            if question_type == QUESTIONTYPE.DISEASE_GOOD_FOOD :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 已知疾病，查忌口食物
            if question_type == QUESTIONTYPE.DISEASE_AOID_FOOD :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 已知疾病，查检查项目
            if question_type == QUESTIONTYPE.DISEASE_DO_CHECK :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 预防
            if question_type == QUESTIONTYPE.DISEASE_PREVENT :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 治疗方法
            if question_type == QUESTIONTYPE.DISEASE_TREAT_WAY :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 可能性
            if question_type == QUESTIONTYPE.DISEASE_CURED_PRO :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 治愈周期
            if question_type == QUESTIONTYPE.DISEASE_TREAT_CYCLE:
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 科室
            if question_type == QUESTIONTYPE.DISEASE_TO_DEPARTMENT:
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            # 疾病描述
            if question_type == QUESTIONTYPE.DISEASE_DESC :
                sql = self.sql_transfer(question_type,entity_dict.get(ENTITYTYPE.DISEASE))
            
            sql_dict = {}
            sql_dict['question_type'] = question_type
            if sql:
                sql_dict['sql'] = sql
                sql_list.append(sql_dict)
            
            return sql_list
    
    def sql_transfer(self,question_type,entities):
        if not entities:
            return []
        
        sql = []
        #TODO 1 已知疾病查询症状 disease_symptom
        if question_type == QUESTIONTYPE.DISEASE_TO_SYMPTOM:
            sql = ["MATCH (m:Disease)-[r:has_symptom]->(n:Symptom) where m.name = '{0}' " \
				   "return m.name, r.name, n.name".format(i) for i in entities]

		#TODO 2 已知症状判断疾病 symptom_disease
        elif question_type == QUESTIONTYPE.SYMPTOM_TO_DISEASE:
            sql = ["MATCH (m:Disease)-[r:has_symptom]->(n:Symptom) where n.name = '{0}' " \
				   "return m.name, r.name, n.name".format(i) for i in entities]

		#TODO 3 疾病原因 disease_cause
        elif question_type == QUESTIONTYPE.DISEASE_CAUSE:
            sql = ["MATCH (m:Disease) where m.name = '{0}' " \
				   "return m.name, m.cause".format(i) for i in entities]

		#TODO 4 并发症 disease_complication
        elif question_type == QUESTIONTYPE.DISEASE_COMLICATION:
            sql = ["MATCH (m:Disease)-[r:acompany_with]->(n:Disease) where m.name = '{0}' " \
				   "return m.name, r.name, n.name".format(i) for i in entities]

		#TODO 5 已知疾病查忌口食物 disease_avoid_food
        elif question_type == QUESTIONTYPE.DISEASE_AOID_FOOD:
            sql = ["MATCH (m:Disease)-[r:no_eat]->(n:Food) where m.name = '{0}' return m.name, r.name, n.name".format(i) for i in entities]

		#TODO 已知疾病查推荐食物  disease_good_food
        elif question_type == QUESTIONTYPE.DISEASE_GOOD_FOOD:
            sql1 = ["MATCH (m:Disease)-[r:do_eat]->(n:Food) where m.name = '{0}' return m.name, r.name, n.name".format(i) for i in entities]
            sql2 = ["MATCH (m:Disease)-[r:recommand_eat]->(n:Food) where m.name = '{0}' return m.name, r.name, n.name".format(i) for i in entities]
            sql = sql1 + sql2

		#TODO 7 疾病常用药品 disease_drug
        elif question_type == QUESTIONTYPE.DISEASE_DRUG:
            sql = ["MATCH (m:Disease)-[r:common_drug]->(n:Drug) where m.name = '{0}' return m.name, r.name, n.name".format(i) for i in entities]

		#TODO 8 疾病检查项目 disease_check
        elif question_type == QUESTIONTYPE.DISEASE_DO_CHECK :
            sql = ["MATCH (m:Disease)-[r:need_check]->(n:Check) where m.name = '{0}' return m.name, r.name, n.name".format(i) for i in entities]

		#TODO 11 疾病预防 disease_prevent
        elif question_type == QUESTIONTYPE.DISEASE_PREVENT:
            sql = ["MATCH (m:Disease) where m.name = '{0}' return m.name, m.prevent".format(i) for i in entities]

		#TODO 12 疾病治疗方法 disease_treat_way
        elif question_type == QUESTIONTYPE.DISEASE_TREAT_WAY:
            sql = ["MATCH (m:Disease) where m.name = '{0}' return m.name, m.cure_way".format(i) for i in entities]

		#TODO 13 疾病治愈可能性 disease_cure_prob
        elif question_type == QUESTIONTYPE.DISEASE_CURED_PRO:
            sql = ["MATCH (m:Disease) where m.name = '{0}' return m.name, m.cured_prob".format(i) for i in entities]

		#TODO 14 疾病去哪个科室 disease_department
        elif question_type == QUESTIONTYPE.DISEASE_TO_DEPARTMENT:
            sql = ["MATCH (m:Disease)-[r:belongs_to]->(n:Department) where m.name = '{0}' return m.name,r.name,n.name".format(i) for i in entities]

		#TODO 15 疾病治疗周期 disease_treat_cycle
        elif question_type == QUESTIONTYPE.DISEASE_TREAT_CYCLE:
            sql = ["MATCH (m:Disease) where m.name = '{0}' return m.name, m.cure_lasttime".format(i) for i in entities]

		# TODO 16 疾病描述 
        elif question_type == QUESTIONTYPE.DISEASE_DESC:
            sql = ["MATCH (m:Disease) where m.name = '{0}' return m.name, m.desc".format(i) for i in entities]

        return sql

    def extract_entity(self,keywords):
        '''
        :param keywords: (entity, [entity_label_list])
        :return:
        '''
        entity_dict = {}
        for entity, types in keywords.items():
            for type in types:
                if type in entity_dict:
                    entity_dict[type].append(entity)
                else:
                    entity_dict[type] = [entity]
        return entity_dict


class AnswerSearcher(object):
    def __init__(self):
        self.g = Graph(password="0314")
        self.num_limit = 20


    def search_main(self,sql_list):
        final_answers = []
        for sql_dict in sql_list:
            question_type = sql_dict['question_type']
            querys = sql_dict['sql']
            answers = []
            for query in querys:
                ress = self.g.run(query).data()
                answers += ress
            final_answer = self.answer_prettify(question_type,answers)
            if final_answer:
                final_answers.append(final_answer)
        return final_answers

    '''根据对应的qustion_type，调用相应的回复模板'''
    def answer_prettify(self, question_type, answers):
        final_answer = []
        if not answers:
            return ''
        if question_type == QUESTIONTYPE.DISEASE_TO_SYMPTOM:
            desc = [i['n.name'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}的症状包括：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.SYMPTOM_TO_DISEASE:
            desc = [i['m.name'] for i in answers]
            subject = answers[0]['n.name']
            final_answer = '症状{0}可能染上的疾病有：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_CAUSE:
            desc = [i['m.cause'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}可能的成因有：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_PREVENT:
            desc = [i['m.prevent'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}的预防措施包括：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_TREAT_CYCLE:
            desc = [i['m.cure_lasttime'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}治疗可能持续的周期为：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_TREAT_WAY:
            desc = [';'.join(i['m.cure_way']) for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}可以尝试如下治疗：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_CURED_PRO:
            desc = [i['m.cured_prob'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}治愈的概率为（仅供参考）：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_DESC:
            desc = [i['m.desc'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0},熟悉一下：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_COMLICATION:
            desc = [i['n.name'] for i in answers]
            # desc2 = [i['m.name'] for i in answers]
            subject = answers[0]['m.name']
            # desc = [i for i in desc1 + desc2 if i != subject]
            final_answer = '{0}的并发症包括：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_COMLICATION:
            desc = [i['n.name'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}忌食的食物包括有：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_GOOD_FOOD:
            do_desc = [i['n.name'] for i in answers if i['r.name'] == '宜吃']
            recommand_desc = [i['n.name'] for i in answers if i['r.name'] == '推荐食谱']
            subject = answers[0]['m.name']
            final_answer = '{0}宜食的食物包括有：{1}\n推荐食谱包括有：{2}'.format(subject, ';'.join(list(set(do_desc))[:self.num_limit]),
                                                                    ';'.join(list(set(recommand_desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_AOID_FOOD:
            desc = [i['m.name'] for i in answers]
            subject = answers[0]['n.name']
            final_answer = '患有{0}的人最好不要吃{1}'.format('；'.join(list(set(desc))[:self.num_limit]), subject)

        elif question_type == QUESTIONTYPE.DISEASE_DRUG:
            desc = [i['n.name'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}通常的使用的药品包括：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))


        elif question_type == QUESTIONTYPE.DISEASE_DO_CHECK:
            desc = [i['n.name'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}通常可以通过以下方式检查出来：{1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        elif question_type == QUESTIONTYPE.DISEASE_TO_DEPARTMENT:
            desc = [i['n.name'] for i in answers]
            subject = answers[0]['m.name']
            final_answer = '{0}所属科室为： {1}'.format(subject, '；'.join(list(set(desc))[:self.num_limit]))

        return final_answer

class QuestionAnswerSystem(object):
	def __init__(self):
		self.classifier = QuestionClassifier()
		self.question_parser = QuestionParser()
		self.answer_searcher = AnswerSearcher()

	def question_answer_main(self,question):
		answer = "非常抱歉，这个问题超出小医的能力范围！"
		# 问题分类
		classify_res = self.classifier.classify_main(question)
		print(classify_res)
		if not classify_res: # 无法解析问句
			return answer
		
		# 问题解析
		res_sql = self.question_parser.parser_main(classify_res)
		print(res_sql)
		final_answers = self.answer_searcher.search_main(res_sql)

		if not final_answers:
			return answer
		else:
			return '\n'.join(final_answers)

if __name__=="__main__":
    handler = QuestionAnswerSystem()
    while True:
        question = input("用户:")
        answer = handler.question_answer_main(question)
        print(answer)